from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import cv2
import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import create_task, get_task, update_task
from app.main import app
from app.services.audit_engine import run_audit
from app.services.bailian_client import ModelClient
from app.services import official_monitoring
from app.services import vision_agent


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, 'DATABASE_PATH', str(tmp_path / 'pc-bugs.sqlite3'))
    monkeypatch.setattr(settings, 'UPLOAD_DIR', str(tmp_path / 'uploads'))
    monkeypatch.setattr(settings, 'REPORT_DIR', str(tmp_path / 'reports'))
    async def unused_public_sync():
        return {'sourceId': 'test-public-stub', 'status': 'error'}
    monkeypatch.setattr(official_monitoring, 'sync_public_dataset', unused_public_sync)
    monkeypatch.setattr(official_monitoring, 'sync_watched_trademarks', unused_public_sync)
    with TestClient(app) as instance:
        yield instance


def guest(client):
    data = client.post('/api/auth/guest').json()['data']
    return {'Authorization': 'Bearer ' + data['token']}, data['user']['userId']


def complete_task(user_id):
    task_id = uuid4().hex
    create_task(task_id, user_id, {'brandName': 'PC验收独立图样', 'englishName': 'PC Original Pattern', 'niceClass': '第25类-服装鞋帽', 'targetCountries': ['越南']})
    update_task(task_id, status='done', progress=100, result={'riskLevel': 'low', 'riskScore': 18, 'manualReviewRequired': True, 'reportSchemaVersion': 2, 'summary': {'brandName': 'PC验收独立图样', 'riskLevel': 'low', 'riskScore': 18}})
    return task_id


def test_reading_completed_report_never_changes_archive_or_modified_time(client):
    headers, user_id = guest(client)
    task_id = complete_task(user_id)
    before = get_task(task_id)
    for _ in range(2):
        response = client.get('/api/audit/result/' + task_id, headers=headers)
        assert response.status_code == 200
        assert response.json()['data']['status'] == 'done'
    after = get_task(task_id)
    for field in ('createdAt', 'updatedAt', 'completedAt', 'archivedAt'):
        assert after[field] == before[field]
    assert after['lastViewedAt']
    record = client.get('/api/reports', headers=headers).json()['data'][0]
    assert record['archivedAt'] == before['archivedAt']
    assert record['lastViewedAt'] == after['lastViewedAt']


def test_task_list_is_private_and_completed_tasks_are_navigable(client):
    owner, user_id = guest(client)
    stranger, _ = guest(client)
    task_id = complete_task(user_id)
    assert [task['taskId'] for task in client.get('/api/audit/tasks', headers=owner).json()['data']] == [task_id]
    assert client.get('/api/audit/tasks', headers=stranger).json()['data'] == []
    assert client.get('/api/audit/tasks').status_code == 401


def test_pdf_generation_rejects_empty_bytes(client, monkeypatch):
    headers, user_id = guest(client)
    task_id = complete_task(user_id)
    monkeypatch.setattr('app.api.audit.build_audit_pdf', lambda result: b'')
    response = client.get(f'/api/audit/report/{task_id}/pdf', headers=headers)
    assert response.status_code == 503
    assert '文件生成失败' in response.json()['detail']


def test_complexity_and_symmetry_do_not_raise_legal_risk_score(monkeypatch):
    extract_features = vision_agent.extract_visual_features
    monkeypatch.setattr(vision_agent, 'extract_visual_features', lambda image: replace(extract_features(image), review_score=90))
    image = np.full((240, 240, 3), 255, dtype=np.uint8)
    for center in ((120, 60), (180, 120), (120, 180), (60, 120)):
        cv2.circle(image, center, 40, (0, 0, 0), 10)
    _, encoded = cv2.imencode('.png', image)
    result = run_audit({'brandName': 'Original Cloudring Pattern', 'englishName': 'Original Cloudring Pattern', 'niceClass': '第25类-服装鞋帽', 'goodsServices': '原创几何图样服装', 'logo': base64.b64encode(encoded).decode()})
    assert any(rule.get('ruleId') == 'VN-INFO-004' for rule in result['hitRules'])
    assert result['riskScore'] == 18
    assert result['assessmentStatus'] == 'pending_verification'
    assert result['manualReviewRequired'] is True
    assert '待核验，不作法律风险评级' in result['documentPreview']
    assert all(reference.get('sourceKind') == 'internal_rule' for reference in result['references'])


def test_deepseek_selection_and_compatible_api_payload(monkeypatch):
    monkeypatch.setattr(settings, 'MODEL_PROVIDER', 'deepseek')
    monkeypatch.setattr(settings, 'GLM_API_KEY', 'test-glm-not-selected')
    monkeypatch.setattr(settings, 'DEEPSEEK_API_KEY', 'test-deepseek-only')
    monkeypatch.setattr(settings, 'DEEPSEEK_MODEL', 'deepseek-flash')
    seen = []
    def response(request):
        seen.append(request)
        return httpx.Response(200, json={'choices': [{'message': {'content': '仅为资料线索，需回查原文。'}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **options: original(transport=httpx.MockTransport(response), **options))
    assert asyncio.run(ModelClient().complete([{'role': 'user', 'content': '核对资料入口'}]))
    assert str(seen[0].url) == 'https://api.deepseek.com/chat/completions'
    assert seen[0].headers['Authorization'] == 'Bearer test-deepseek-only'
    assert json.loads(seen[0].content)['model'] == 'deepseek-flash'
    assert 'thinking' not in json.loads(seen[0].content)


def test_official_parser_rejects_external_links_and_deduplicates():
    source = official_monitoring.OFFICIAL_SOURCES[0]
    html = '<a href="/news/news-collection/real-notice/">真实官方公告标题</a><a href="/news/news-collection/real-notice/">真实官方公告标题</a><a href="https://attacker.example/news/news-collection/fake">外部伪造公告标题</a>'
    entries = official_monitoring.parse_official_links(source, html)
    assert len(entries) == 1
    assert entries[0]['url'].startswith('https://www.ipos.gov.sg/')


def test_official_sync_records_baseline_then_new_items_without_duplicates(client, monkeypatch):
    source = {**official_monitoring.OFFICIAL_SOURCES[0], 'collectionAllowed': True}
    monkeypatch.setattr(official_monitoring, 'OFFICIAL_SOURCES', (source,))
    contents = ['<a href="/news/news-collection/notice-one/">首轮采集官方条目</a>']
    def response(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-Agent: *\nAllow: /')
        return httpx.Response(200, text=contents[0], headers={'content-type': 'text/html'})
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **options: original(transport=httpx.MockTransport(response), **options))
    first = asyncio.run(official_monitoring.sync_official_sources())
    assert first['sources'][0]['baseline'] is True
    assert first['sources'][0]['inserted'] == 1
    second = asyncio.run(official_monitoring.sync_official_sources())
    assert second['sources'][0]['inserted'] == 0
    contents[0] += '<a href="/news/news-collection/notice-two/">后续采集官方新条目</a>'
    third = asyncio.run(official_monitoring.sync_official_sources())
    assert third['sources'][0]['inserted'] == 1
    alerts = official_monitoring.official_alerts()
    assert {alert['status'] for alert in alerts} == {'基线资料', '新采集线索'}
    assert all(alert['isDemo'] is False for alert in alerts)
    assert all(alert['window'] == '未核算法定期限' for alert in alerts)


def test_robots_disallow_is_observed_and_source_not_marked_online(client, monkeypatch):
    source = {**official_monitoring.OFFICIAL_SOURCES[0], 'collectionAllowed': True}
    monkeypatch.setattr(official_monitoring, 'OFFICIAL_SOURCES', (source,))
    requests = []
    def response(request):
        requests.append(request.url.path)
        return httpx.Response(200, text='User-Agent: *\nDisallow: /')
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **options: original(transport=httpx.MockTransport(response), **options))
    result = asyncio.run(official_monitoring.sync_official_sources())
    assert result['successfulSources'] == 0
    assert requests == ['/robots.txt']
    assert official_monitoring.official_source_status()[0]['status'] == 'degraded'
    assert official_monitoring.official_alerts() == []


def test_ordinary_user_cannot_trigger_data_collection(client):
    headers, _ = guest(client)
    assert client.post('/api/monitoring/sync', headers=headers).status_code == 403


def test_singapore_checklist_has_real_provenance_but_does_not_bypass_approval(client):
    headers, _ = guest(client)
    response = client.get('/api/legal/scenario-checklists?country_code=SG&legal_module=M5', headers=headers)
    assert response.status_code == 200
    checklist = response.json()[0]
    assert checklist['approvalStatus'] == 'draft'
    assert checklist['sourceUrl'].startswith('https://www.ipos.gov.sg/')
    assert checklist['lawUrl'] == 'https://sso.agc.gov.sg/Act/TMA1998'
    assert len(checklist['checks']) == 5
    assert '2026-09-03' in checklist['sourceVersion']
    assert '尚未核实' in checklist['lawVersion']
    assert client.get('/api/legal/scenario-checklists?country_code=VN&legal_module=M5', headers=headers).json() == []
    assert client.get('/api/legal/scenario-checklists?country_code=SG&legal_module=M2', headers=headers).json() == []
    assert client.get('/api/legal/sources?country_code=SG&legal_module=M5', headers=headers).json() == []


def test_report_api_keeps_internal_rule_identifiers_for_traceability(client):
    headers, user_id = guest(client)
    task_id = complete_task(user_id)
    result = get_task(task_id)['result']
    result['hitRules'] = [{'ruleId': 'VN-INFO-004', 'ruleName': '复杂图形仅供人工复核', 'ruleType': 'absolute', 'article': '内部图形复核规则', 'content': '不是正式法条', 'applicable': True, 'similarityScore': 90, 'similarityType': '技术特征', 'note': '不能代替真实在先权利比对'}]
    update_task(task_id, result=result)
    response = client.get(f'/api/audit/result/{task_id}', headers=headers)
    assert response.status_code == 200
    assert response.json()['data']['hitRules'][0]['ruleId'] == 'VN-INFO-004'
    assert response.json()['data']['hitRules'][0]['ruleName'] == '复杂图形仅供人工复核'
