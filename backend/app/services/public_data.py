from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import threading
import time
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.database import _connect, _now


DATASET_ID = "d_6145acb2130bf781165258e76a584383"
DATASET_URL = f"https://data.gov.sg/datasets/{DATASET_ID}/view"
LICENCE_URL = "https://data.gov.sg/open-data-licence"
API_URL = "https://data.gov.sg/api/action/datastore_search"
METADATA_URL = f"https://api-open.data.gov.sg/v2/public/api/datasets/{DATASET_ID}/metadata"
ATTRIBUTION = "Contains information from IPOS Trade Mark Applications accessed via data.gov.sg, made available under the Singapore Open Data Licence."
FIELDS = "applicationNumber,filingDate,applicationDate,markStatus,markStatusDate,statusUpdateDate,expiryDate,publicationDate,lastModifiedDate,markData_json,goodsAndServicesSpecifications_json"
BOUNDARY = "仅查询新加坡 IPOS 开放申请记录。结果不等于图形/读音近似检索、完整在先权利调查或可注册性意见；无结果不表示不存在冲突。状态以官方原文和数据更新时间为准。"
_pacing_guard = threading.Lock()
_next_request = 0.0


class PublicDataError(RuntimeError):
    pass


def init_public_data_database() -> None:
    with _connect() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS public_dataset_state (dataset_id TEXT PRIMARY KEY, checked_at TEXT, succeeded_at TEXT, updated_at TEXT, total_records INTEGER NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '')")
        connection.execute("CREATE TABLE IF NOT EXISTS public_trademark_records (application_number TEXT PRIMARY KEY, record_json TEXT NOT NULL, first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, fingerprint TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS public_query_cache (cache_key TEXT PRIMARY KEY, fetched_at TEXT NOT NULL, result_json TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS public_trademark_events (event_id TEXT PRIMARY KEY, application_number TEXT NOT NULL, event_type TEXT NOT NULL, observed_at TEXT NOT NULL, previous_json TEXT, current_json TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS public_trademark_watches (user_id TEXT NOT NULL, application_number TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(user_id, application_number))")
        connection.execute("CREATE TABLE IF NOT EXISTS public_watch_sync_state (state_id INTEGER PRIMARY KEY CHECK (state_id = 1), checked_at TEXT NOT NULL, count INTEGER NOT NULL, error TEXT NOT NULL)")


async def _fetch_json(address: str, params: dict | None = None) -> dict:
    global _next_request
    with _pacing_guard:
        now = time.monotonic()
        slot = max(now, _next_request)
        if slot - now > 30:
            raise PublicDataError("当前官方数据请求队列已满，请稍后重试。")
        _next_request = slot + 3.0
    await asyncio.sleep(max(0, slot - now))
    headers = {"User-Agent": "ASEANLegalOpenData/1.0 (+licensed-api; bounded-requests)"}
    if settings.PUBLIC_DATA_API_KEY:
        headers["x-api-key"] = settings.PUBLIC_DATA_API_KEY
    try:
        async with httpx.AsyncClient(timeout=35, follow_redirects=False) as client:
            async with client.stream("GET", address, params=params, headers=headers) as response:
                if response.status_code == 429:
                    raise PublicDataError("官方开放数据接口限流，请稍后重试；不会绕过限制。")
                response.raise_for_status()
                if "json" not in response.headers.get("content-type", ""):
                    raise PublicDataError("官方接口未返回 JSON，需人工核对接口状态。")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 3_000_000:
                        raise PublicDataError("官方返回超过大小上限，请缩小检索范围。")
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise PublicDataError("官方返回数据结构不正确。")
        return payload
    except (httpx.HTTPError, ValueError) as failure:
        raise PublicDataError("官方开放数据暂不可用，请稍后重试；不使用演示数据代替。") from failure


def _nested_array(value: object) -> list[dict]:
    try:
        result = json.loads(value) if isinstance(value, str) else value
    except (ValueError, TypeError):
        return []
    return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []


def normalize_record(row: dict, fetched_at: str) -> dict:
    application_number = str(row.get("applicationNumber") or "")[:80]
    if not application_number:
        raise PublicDataError("官方记录缺少申请号，拒绝保存不完整数据。")
    mark_data = _nested_array(row.get("markData_json"))
    specifications = _nested_array(row.get("goodsAndServicesSpecifications_json"))
    classes = []
    goods_services = []
    for specification in specifications:
        class_name = str(specification.get("classNum") or "")[:60]
        if class_name:
            classes.append(class_name)
        for item in specification.get("goodsServices") or []:
            if isinstance(item, dict) and item.get("itemDesc"):
                goods_services.append(str(item["itemDesc"])[:400])
    return {
        "applicationNumber": application_number,
        "markName": " / ".join(str(item.get("wordsInMark") or item.get("chineseCharacter") or "")[:400] for item in mark_data).strip(" / ") or "无文字商标（需查图样）",
        "classes": sorted(set(classes)),
        "goodsServices": goods_services[:12],
        "goodsServicesTruncated": len(goods_services) > 12,
        "status": str(row.get("markStatus") or "未提供")[:100],
        "applicationDate": row.get("applicationDate") or row.get("filingDate"),
        "statusDate": row.get("markStatusDate"),
        "expiryDate": row.get("expiryDate"),
        "publicationDate": row.get("publicationDate"),
        "officialModifiedAt": row.get("lastModifiedDate"),
        "fetchedAt": fetched_at,
        "sourceUrl": API_URL + "?" + urlencode({"resource_id": DATASET_ID, "filters": json.dumps({"applicationNumber": application_number}), "fields": FIELDS, "limit": 1}),
        "datasetUrl": DATASET_URL,
        "licenceUrl": LICENCE_URL,
        "attribution": ATTRIBUTION,
        "isDemo": False,
    }


def _save_records(records: list[dict], fetched_at: str) -> int:
    inserted = 0
    with _connect() as connection:
        for record in records:
            try:
                original_fetched = datetime.fromisoformat(record["fetchedAt"])
            except (ValueError, TypeError):
                raise PublicDataError("采集时间不完整，拒绝覆盖记录。")
            stable = {key: value for key, value in record.items() if key != "fetchedAt"}
            fingerprint = hashlib.sha256(json.dumps(stable, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            existing = connection.execute("SELECT fingerprint, record_json FROM public_trademark_records WHERE application_number = ?", (record["applicationNumber"],)).fetchone()
            if existing and datetime.fromisoformat(json.loads(existing["record_json"])["fetchedAt"]) > original_fetched:
                continue
            inserted += int(existing is None)
            if existing is None or existing["fingerprint"] != fingerprint:
                event_id = hashlib.sha256((record["applicationNumber"] + fingerprint + fetched_at).encode()).hexdigest()
                connection.execute("INSERT INTO public_trademark_events VALUES (?, ?, ?, ?, ?, ?)", (event_id, record["applicationNumber"], "first_seen" if existing is None else "changed", fetched_at, existing["record_json"] if existing else None, json.dumps(record, ensure_ascii=False)))
            connection.execute("INSERT INTO public_trademark_records VALUES (?, ?, ?, ?, ?) ON CONFLICT(application_number) DO UPDATE SET record_json=excluded.record_json, last_seen_at=excluded.last_seen_at, fingerprint=excluded.fingerprint", (record["applicationNumber"], json.dumps(record, ensure_ascii=False), fetched_at, fetched_at, fingerprint))
    return inserted


def _records_from_payload(payload: dict, fetched_at: str) -> tuple[list[dict], int]:
    result = payload.get("result")
    if payload.get("success") is not True or not isinstance(result, dict) or not isinstance(result.get("records"), list):
        raise PublicDataError("官方查询未成功，拒绝将错误响应当作零结果。")
    try:
        total = int(result["total"])
        if total < 0 or any(not isinstance(row, dict) for row in result["records"]):
            raise ValueError
        return [normalize_record(row, fetched_at) for row in result["records"]], total
    except (ValueError, TypeError, KeyError) as failure:
        raise PublicDataError("官方返回了不完整的记录或总数。") from failure


async def sync_public_dataset() -> dict:
    init_public_data_database()
    timestamp = _now()
    try:
        metadata = await _fetch_json(METADATA_URL)
        details = metadata.get("data", {})
        if metadata.get("code") != 0 or not isinstance(details, dict) or details.get("datasetId") != DATASET_ID or not details.get("lastUpdatedAt"):
            raise PublicDataError("官方数据集元数据不完整，未标记为同步成功。")
        payload = await _fetch_json(API_URL, {"resource_id": DATASET_ID, "fields": FIELDS, "limit": 25, "sort": "lastModifiedDate desc,applicationNumber"})
        records, total = _records_from_payload(payload, timestamp)
        if not records:
            raise PublicDataError("官方数据集未返回基线记录，需核对数据集状态。")
        inserted = _save_records(records, timestamp)
        with _connect() as connection:
            connection.execute("INSERT INTO public_dataset_state VALUES (?, ?, ?, ?, ?, '') ON CONFLICT(dataset_id) DO UPDATE SET checked_at=excluded.checked_at, succeeded_at=excluded.succeeded_at, updated_at=excluded.updated_at, total_records=excluded.total_records, error=''", (DATASET_ID, timestamp, timestamp, details["lastUpdatedAt"], total))
        return {"sourceId": "ipos-open-trademarks", "status": "ok", "count": len(records), "inserted": inserted, "remoteTotal": total, "datasetUpdatedAt": details["lastUpdatedAt"], "baseline": True}
    except PublicDataError as failure:
        with _connect() as connection:
            connection.execute("INSERT INTO public_dataset_state (dataset_id, checked_at, error) VALUES (?, ?, ?) ON CONFLICT(dataset_id) DO UPDATE SET checked_at=excluded.checked_at, error=excluded.error", (DATASET_ID, timestamp, str(failure)))
        return {"sourceId": "ipos-open-trademarks", "status": "error", "error": str(failure)}


def watch_trademark(user_id: str, application_number: str) -> dict:
    init_public_data_database()
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        if not connection.execute("SELECT 1 FROM public_trademark_records WHERE application_number = ?", (application_number,)).fetchone():
            raise PublicDataError("请先检索取得官方记录再添加关注。")
        if connection.execute("SELECT 1 FROM public_trademark_watches WHERE user_id = ? AND application_number = ?", (user_id, application_number)).fetchone():
            return {"applicationNumber": application_number, "watching": True}
        personal = connection.execute("SELECT count(*) FROM public_trademark_watches WHERE user_id = ?", (user_id,)).fetchone()[0]
        global_count = connection.execute("SELECT count(DISTINCT application_number) FROM public_trademark_watches").fetchone()[0]
        already_tracked = connection.execute("SELECT 1 FROM public_trademark_watches WHERE application_number = ?", (application_number,)).fetchone()
        if personal >= 10 or (global_count >= 30 and not already_tracked):
            raise PublicDataError("当前受限于开放接口配额，每用户最多 10 条、系统最多 30 个不同申请号；请取消旧关注或配置更高额度的数据接口。")
        connection.execute("INSERT INTO public_trademark_watches VALUES (?, ?, ?)", (user_id, application_number, _now()))
    return {"applicationNumber": application_number, "watching": True}


def unwatch_trademark(user_id: str, application_number: str) -> dict:
    init_public_data_database()
    with _connect() as connection:
        connection.execute("DELETE FROM public_trademark_watches WHERE user_id = ? AND application_number = ?", (user_id, application_number))
    return {"applicationNumber": application_number, "watching": False}


def watched_trademarks(user_id: str) -> list[dict]:
    init_public_data_database()
    with _connect() as connection:
        rows = connection.execute("SELECT record_json FROM public_trademark_records JOIN public_trademark_watches USING(application_number) WHERE user_id = ? ORDER BY public_trademark_watches.created_at DESC", (user_id,)).fetchall()
    return [json.loads(row["record_json"]) for row in rows]


async def sync_watched_trademarks() -> dict:
    init_public_data_database()
    with _connect() as connection:
        numbers = [row["application_number"] for row in connection.execute("SELECT DISTINCT application_number FROM public_trademark_watches ORDER BY application_number LIMIT 30")]
    checked = 0
    for application_number in numbers:
        try:
            timestamp = _now()
            payload = await _fetch_json(API_URL, {"resource_id": DATASET_ID, "filters": json.dumps({"applicationNumber": application_number}), "fields": FIELDS, "limit": 1})
            records, _ = _records_from_payload(payload, timestamp)
            if len(records) != 1 or records[0]["applicationNumber"] != application_number:
                raise PublicDataError("已关注申请号未返回唯一官方记录，原记录保留且不推断删除/失效。")
            _save_records(records, timestamp)
            checked += 1
        except PublicDataError as failure:
            with _connect() as connection:
                connection.execute("INSERT INTO public_watch_sync_state VALUES (1, ?, ?, ?) ON CONFLICT(state_id) DO UPDATE SET checked_at=excluded.checked_at, count=excluded.count, error=excluded.error", (_now(), checked, str(failure)))
            return {"sourceId": "ipos-watched-trademarks", "status": "error", "count": checked, "error": str(failure)}
    with _connect() as connection:
        connection.execute("INSERT INTO public_watch_sync_state VALUES (1, ?, ?, '') ON CONFLICT(state_id) DO UPDATE SET checked_at=excluded.checked_at, count=excluded.count, error=''", (_now(), checked))
    return {"sourceId": "ipos-watched-trademarks", "status": "ok", "count": checked}


def public_dataset_status() -> dict:
    init_public_data_database()
    with _connect() as connection:
        row = connection.execute("SELECT * FROM public_dataset_state WHERE dataset_id = ?", (DATASET_ID,)).fetchone()
        count = connection.execute("SELECT count(*) FROM public_trademark_records").fetchone()[0]
        watch_row = connection.execute("SELECT * FROM public_watch_sync_state WHERE state_id = 1").fetchone()
    state = dict(row) if row else {}
    succeeded = state.get("succeeded_at")
    watch_error = watch_row["error"] if watch_row else ""
    stale = bool(succeeded and (datetime.now(timezone.utc) - datetime.fromisoformat(succeeded)).total_seconds() > settings.MONITORING_INTERVAL_SECONDS * 2)
    return {"name": "IPOS 商标申请开放数据", "type": "官方开放 API（Singapore Open Data Licence）", "status": "degraded" if state.get("error") or watch_error or stale else "online" if succeeded else "scheduled", "coverage": 0, "recordCount": count, "remoteRecordCount": state.get("total_records", 0), "datasetUpdatedAt": state.get("updated_at"), "freshness": "每 6 小时核对元数据及 25 条基线；检索按需请求" if settings.MONITORING_ENABLED else "定时同步未启用；仍可按需检索", "lastSync": succeeded or "尚未同步", "note": state.get("error") or ("关注复查失败：" + watch_error if watch_error else BOUNDARY), "sourceUrl": DATASET_URL, "licenceUrl": LICENCE_URL, "attribution": ATTRIBUTION}


async def search_public_trademarks(query: str, offset: int = 0) -> dict:
    init_public_data_database()
    query = query.strip()
    if len(query) < 2 or len(query) > 100 or offset < 0 or offset > 100:
        raise PublicDataError("检索词需为 2–100 字，分页偏移不能超过 100。")
    cache_key = hashlib.sha256(json.dumps([query.casefold(), offset]).encode()).hexdigest()
    with _connect() as connection:
        cached = connection.execute("SELECT * FROM public_query_cache WHERE cache_key = ?", (cache_key,)).fetchone()
    if cached and (datetime.now(timezone.utc) - datetime.fromisoformat(cached["fetched_at"])).total_seconds() < 21600:
        return {**json.loads(cached["result_json"]), "cached": True}
    fetched_at = _now()
    payload = await _fetch_json(API_URL, {"resource_id": DATASET_ID, "q": json.dumps({"markData_json": query}), "fields": FIELDS, "limit": 10, "offset": offset})
    records, total = _records_from_payload(payload, fetched_at)
    _save_records(records, fetched_at)
    status = public_dataset_status()
    result = {"query": query, "records": records, "total": total, "offset": offset, "limit": 10, "hasMore": offset + len(records) < total and offset < 100, "fetchedAt": fetched_at, "datasetUpdatedAt": status["datasetUpdatedAt"], "cached": False, "boundary": BOUNDARY, "sourceUrl": DATASET_URL, "licenceUrl": LICENCE_URL, "attribution": ATTRIBUTION, "isDemo": False}
    with _connect() as connection:
        connection.execute("INSERT INTO public_query_cache VALUES (?, ?, ?) ON CONFLICT(cache_key) DO UPDATE SET fetched_at=excluded.fetched_at, result_json=excluded.result_json", (cache_key, fetched_at, json.dumps(result, ensure_ascii=False)))
        connection.execute("DELETE FROM public_query_cache WHERE cache_key NOT IN (SELECT cache_key FROM public_query_cache ORDER BY fetched_at DESC LIMIT 200)")
    return result


def public_trademark_alerts(user_id: str | None = None) -> list[dict]:
    init_public_data_database()
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM public_trademark_events WHERE event_type = 'first_seen' OR application_number IN (SELECT application_number FROM public_trademark_watches WHERE user_id = ?) ORDER BY observed_at DESC, application_number LIMIT 25", (user_id or "",)).fetchall()
    alerts = []
    for row in rows:
        record = json.loads(row["current_json"])
        event_type = "数据变更（待核对）" if row["event_type"] == "changed" else "首次收录（非新申请）"
        alerts.append({"alertId": "SG-" + row["event_id"][:12], "title": f"{record['markName']} · {record['applicationNumber']}", "severity": "low", "country": "新加坡", "brandName": "公共申请记录（未判定品牌冲突）", "source": "IPOS / data.gov.sg 开放数据", "sourceUrl": record["sourceUrl"], "window": "未核算法定期限", "status": event_type + " · " + record["status"], "owner": "待人工复核", "createdAt": row["observed_at"], "lastCheckedAt": record["fetchedAt"], "isDemo": False, "recommendation": BOUNDARY, "licenceUrl": LICENCE_URL, "attribution": ATTRIBUTION, "publicationDate": record["publicationDate"]})
    return alerts
