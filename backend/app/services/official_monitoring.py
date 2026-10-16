from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import settings
from app.database import _connect, _now
from app.services.public_data import public_dataset_status, public_trademark_alerts, sync_public_dataset, sync_watched_trademarks


OFFICIAL_SOURCES = (
    {"id": "ipos-news", "name": "IPOS 官方新闻", "url": "https://www.ipos.gov.sg/news/news-collection/", "country": "新加坡", "kind": "announcement", "paths": ("/news/news-collection/",), "collectionAllowed": False},
    {"id": "ipos-trademark-circulars", "name": "IPOS 商标通告", "url": "https://www.ipos.gov.sg/about-ip/trade-marks/circulars-and-practice-directions/", "country": "新加坡", "kind": "trademark_notice", "paths": ("circular", "practice-direction"), "collectionAllowed": False},
    {"id": "ipos-legislation", "name": "IPOS 官方立法索引", "url": "https://www.ipos.gov.sg/global-ip-hub/statistics-and-legislation-developments/ip-legislation/", "country": "新加坡", "kind": "legislation", "paths": ("sso.agc.gov.sg/Act/TMA", "sso.agc.gov.sg/SL/TMA"), "collectionAllowed": False},
)


class OfficialLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.href = ""
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.href = dict(attrs).get("href") or ""
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.href:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.href:
            self.links.append((self.href, " ".join(" ".join(self.parts).split())))
            self.href = ""
            self.parts = []


def parse_official_links(source: dict, html: str) -> list[dict]:
    parser = OfficialLinks()
    parser.feed(html)
    entries: dict[str, dict] = {}
    for href, title in parser.links:
        address = urljoin(source["url"], href)
        parsed = urlparse(address)
        if parsed.scheme != "https" or not any(parsed.hostname == domain or (parsed.hostname or "").endswith("." + domain) for domain in ("ipos.gov.sg", "gov.sg")):
            continue
        if len(title) < 6 or not any(path.lower() in address.lower() for path in source["paths"]):
            continue
        if address.rstrip("/") == source["url"].rstrip("/"):
            continue
        entries[address] = {"url": address, "title": title[:600], "sourceId": source["id"], "kind": source["kind"]}
    return list(entries.values())[:100]


def init_monitoring_database() -> None:
    with _connect() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS official_sync_state (source_id TEXT PRIMARY KEY, checked_at TEXT, succeeded_at TEXT, error TEXT NOT NULL DEFAULT '', entry_count INTEGER NOT NULL DEFAULT 0, fingerprint TEXT NOT NULL DEFAULT '')")
        connection.execute("CREATE TABLE IF NOT EXISTS official_announcements (entry_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, title TEXT NOT NULL, source_url TEXT NOT NULL UNIQUE, kind TEXT NOT NULL, first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, snapshot_version TEXT NOT NULL, is_baseline INTEGER NOT NULL)")


async def sync_official_sources() -> dict:
    init_monitoring_database()
    results = []
    async with httpx.AsyncClient(timeout=25, follow_redirects=False, headers={"User-Agent": "ASEANLegalMonitor/1.0 (+official-public-announcement-index; six-hour-interval)"}) as client:
        for source in OFFICIAL_SOURCES:
            timestamp = _now()
            if not source.get("collectionAllowed"):
                results.append({"sourceId": source["id"], "status": "paused", "error": "网页条款限制自动缓存/提取，已暂停；仅保留官方回查入口。"})
                continue
            try:
                robots_address = urljoin(source["url"], "/robots.txt")
                robots_response = await client.get(robots_address)
                robots_response.raise_for_status()
                robots = RobotFileParser()
                robots.parse(robots_response.text.splitlines())
                if not robots.can_fetch("ASEANLegalMonitor", source["url"]):
                    raise ValueError("官方 robots.txt 不允许采集此入口")
                async with client.stream("GET", source["url"]) as response:
                    response.raise_for_status()
                    if "text/html" not in response.headers.get("content-type", ""):
                        raise ValueError("官方入口返回了非 HTML 内容")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 3_000_000:
                            raise ValueError("官方入口超过采集大小限制")
                entries = parse_official_links(source, body.decode("utf-8", errors="replace"))
                if not entries:
                    raise ValueError("未解析到官方条目，需人工核验入口结构")
                fingerprint = hashlib.sha256(bytes(body)).hexdigest()
                with _connect() as connection:
                    prior = connection.execute("SELECT succeeded_at FROM official_sync_state WHERE source_id = ?", (source["id"],)).fetchone()
                    baseline = not prior or not prior["succeeded_at"]
                    inserted = 0
                    for entry in entries:
                        entry_id = hashlib.sha256(entry["url"].encode()).hexdigest()[:24]
                        cursor = connection.execute("INSERT OR IGNORE INTO official_announcements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (entry_id, source["id"], entry["title"], entry["url"], source["kind"], timestamp, timestamp, fingerprint, int(baseline)))
                        inserted += cursor.rowcount
                        connection.execute("UPDATE official_announcements SET title = ?, last_seen_at = ?, snapshot_version = ? WHERE entry_id = ?", (entry["title"], timestamp, fingerprint, entry_id))
                    connection.execute("INSERT INTO official_sync_state VALUES (?, ?, ?, '', ?, ?) ON CONFLICT(source_id) DO UPDATE SET checked_at=excluded.checked_at, succeeded_at=excluded.succeeded_at, error='', entry_count=excluded.entry_count, fingerprint=excluded.fingerprint", (source["id"], timestamp, timestamp, len(entries), fingerprint))
                results.append({"sourceId": source["id"], "status": "ok", "count": len(entries), "inserted": inserted, "baseline": baseline})
            except (httpx.HTTPError, ValueError) as failure:
                error = str(failure)[:300]
                with _connect() as connection:
                    connection.execute("INSERT INTO official_sync_state (source_id, checked_at, error) VALUES (?, ?, ?) ON CONFLICT(source_id) DO UPDATE SET checked_at=excluded.checked_at, error=excluded.error", (source["id"], timestamp, error))
                results.append({"sourceId": source["id"], "status": "error", "error": error})
    results.append(await sync_public_dataset())
    results.append(await sync_watched_trademarks())
    return {"sources": results, "checkedAt": _now(), "successfulSources": sum(item["status"] == "ok" for item in results)}


def official_source_status() -> list[dict]:
    init_monitoring_database()
    with _connect() as connection:
        state = {row["source_id"]: dict(row) for row in connection.execute("SELECT * FROM official_sync_state")}
    items = []
    for source in OFFICIAL_SOURCES:
        if not source.get("collectionAllowed"):
            items.append({"name": source["name"], "type": "官方网页回查入口（采集暂停）", "status": "scheduled", "coverage": 0, "recordCount": 0, "freshness": "不自动采集", "lastSync": "已暂停", "note": "官方网页条款限制缓存/提取；历史缓存不继续展示，不绕过限制。", "sourceUrl": source["url"]})
            continue
        current = state.get(source["id"], {})
        success = current.get("succeeded_at")
        stale = bool(success and (datetime.now(timezone.utc) - datetime.fromisoformat(success)).total_seconds() > settings.MONITORING_INTERVAL_SECONDS * 2)
        items.append({"name": source["name"], "type": "官方公开索引", "status": "degraded" if current.get("error") or stale else "online" if success else "scheduled", "coverage": 0, "recordCount": current.get("entry_count", 0), "freshness": "每 6 小时采集" if settings.MONITORING_ENABLED else "定时采集未启用", "lastSync": success or "尚未同步", "lastCheckedAt": current.get("checked_at"), "note": current.get("error") or "仅采集官方公开条目；不是全量商标数据库，不计算异议期限。", "sourceUrl": source["url"]})
    items.append(public_dataset_status())
    items.append({"name": "11 国全量商标注册检索", "type": "各国开放/授权数据接口", "status": "scheduled", "coverage": 0, "freshness": "当前仅接入新加坡开放申请数据", "lastSync": "其他国家未接入", "note": "新加坡公开数据支持真实文字检索，不代表 11 国完整商标注册库或商标冲突结论。"})
    items.append({"name": "SSO 新加坡现行法条", "type": "官方法源（访问受限）", "status": "degraded", "coverage": 0, "freshness": "未采集法条正文", "lastSync": "403，未绕过访问限制", "note": "需核对官方自动化采集条款与时间窗口；法源及摘录维持待审，不自动批准。", "sourceUrl": "https://sso.agc.gov.sg/FAQ"})
    return items


def official_alerts(user_id: str | None = None) -> list[dict]:
    init_monitoring_database()
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM official_announcements WHERE kind != 'legislation' ORDER BY first_seen_at DESC, title LIMIT 100").fetchall()
    sources = {source["id"]: source for source in OFFICIAL_SOURCES if source.get("collectionAllowed")}
    return public_trademark_alerts(user_id) + [{"alertId": "OF-" + row["entry_id"][:12], "title": row["title"], "severity": "low", "country": sources[row["source_id"]]["country"], "brandName": "公共公告（未判定品牌冲突）", "source": sources[row["source_id"]]["name"], "sourceUrl": row["source_url"], "window": "未核算法定期限", "status": "基线资料" if row["is_baseline"] else "新采集线索", "owner": "待人工复核", "createdAt": row["first_seen_at"], "lastCheckedAt": row["last_seen_at"], "snapshotVersion": row["snapshot_version"], "isDemo": False, "recommendation": "打开官方原文核对发布日期、适用事项与最新版本；采集时间不是官方发布时间，不据此判断侵权、异议或注册结果。"} for row in rows if row["source_id"] in sources]


def official_legal_pointers() -> list[dict]:
    init_monitoring_database()
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM official_announcements WHERE kind = 'legislation' ORDER BY title").fetchall()
    allowed = {source["id"] for source in OFFICIAL_SOURCES if source.get("collectionAllowed")}
    return [{"id": row["entry_id"], "title": row["title"], "countryCode": "SG", "legalModule": "M5", "sourceUrl": row["source_url"], "publisher": "新加坡知识产权局官方立法索引", "lastCheckedAt": row["last_seen_at"], "snapshotVersion": row["snapshot_version"], "scope": "仅确认新加坡商标法及实施规则的官方回查入口；现行版本和具体条款适用须在原文进一步核验。", "approvalStatus": "official_pointer_only", "prerequisites": ["目标国家为新加坡", "业务范围为商标权利和申请资料", "按实际申请日期核对官方现行版本"], "nonInferences": ["不判断可注册性、侵权、异议期限或主管机关结果", "不是已经完成法律内容审核的 RAG 摘录"]} for row in rows if row["source_id"] in allowed]


async def monitoring_scheduler() -> None:
    while True:
        try:
            await sync_official_sources()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Official announcement collection failed")
        await asyncio.sleep(settings.MONITORING_INTERVAL_SECONDS)
