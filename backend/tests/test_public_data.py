from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
import subprocess

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database import _connect
from app.main import app
from app.models.assistant import AssistantChatRequest
from app.services.assistant_orchestrator import AssistantOrchestrator
from app.services.bailian_client import ModelClient
from app.services import official_monitoring, public_data, public_data_ai
from app.services.public_data_ai import explain_public_record


ROW = {'applicationNumber': 'TEST001', 'markStatus': 'Registered', 'markData_json': json.dumps([{'wordsInMark': 'Asterloom Workshop'}]), 'goodsAndServicesSpecifications_json': json.dumps([{'classNum': 'Class 25', 'goodsServices': [{'itemDesc': 'Clothing'}]}]), 'lastModifiedDate': '2026-10-01', 'publicationDate': '2026-09-01'}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'DATABASE_PATH', str(tmp_path / 'public.sqlite3'))
    monkeypatch.setattr(settings, 'UPLOAD_DIR', str(tmp_path / 'uploads'))
    monkeypatch.setattr(settings, 'REPORT_DIR', str(tmp_path / 'reports'))
    monkeypatch.setattr(public_data, '_next_request', 0.0)
    with TestClient(app) as instance:
        yield instance


def install_fetch(monkeypatch, rows=None, total=1):
    calls = []
    async def fetch(address, params=None):
        calls.append((address, params))
        if address == public_data.METADATA_URL:
            return {'code': 0, 'data': {'datasetId': public_data.DATASET_ID, 'lastUpdatedAt': '2026-10-14T01:50:31+08:00'}}
        return {'success': True, 'result': {'records': [ROW] if rows is None else rows, 'total': total}}
    monkeypatch.setattr(public_data, '_fetch_json', fetch)
    return calls


def guest(client):
    data = client.post('/api/auth/guest').json()['data']
    return {'Authorization': 'Bearer ' + data['token']}, data['user']['userId']


def test_search_uses_mark_field_only_and_preserves_provenance(client, monkeypatch):
    calls = install_fetch(monkeypatch)
    result = asyncio.run(public_data.search_public_trademarks('Asterloom'))
    assert result['isDemo'] is False
    assert result['records'][0]['markName'] == 'Asterloom Workshop'
    assert result['records'][0]['classes'] == ['Class 25']
    assert result['records'][0]['publicationDate'] == '2026-09-01'
    assert 'Singapore Open Data Licence' in result['attribution']
    assert json.loads(calls[0][1]['q']) == {'markData_json': 'Asterloom'}
    assert 'currentApplicantProprietorDetails_json' not in calls[0][1]['fields']
    cached = asyncio.run(public_data.search_public_trademarks('asterloom'))
    assert cached['cached'] is True
    assert len(calls) == 1


def test_zero_results_are_not_a_clearance(client, monkeypatch):
    install_fetch(monkeypatch, rows=[], total=0)
    result = asyncio.run(public_data.search_public_trademarks('Cloudring'))
    assert result['total'] == 0
    assert '无结果不表示不存在冲突' in result['boundary']


def test_bad_data_is_not_saved_as_zero_results(client, monkeypatch):
    async def fetch(address, params=None):
        return {'success': False, 'error': 'unavailable'}
    monkeypatch.setattr(public_data, '_fetch_json', fetch)
    with pytest.raises(public_data.PublicDataError):
        asyncio.run(public_data.search_public_trademarks('Cloudring'))
    with _connect() as connection:
        assert connection.execute('SELECT count(*) FROM public_query_cache').fetchone()[0] == 0


def test_sync_reports_remote_vs_local_counts_and_never_approves_sources(client, monkeypatch):
    install_fetch(monkeypatch, total=880259)
    result = asyncio.run(public_data.sync_public_dataset())
    assert result['remoteTotal'] == 880259
    state = public_data.public_dataset_status()
    assert state['recordCount'] == 1
    assert state['remoteRecordCount'] == 880259
    assert state['datasetUpdatedAt'] == '2026-10-14T01:50:31+08:00'
    with _connect() as connection:
        assert connection.execute("SELECT count(*) FROM legal_sources WHERE approval_status = 'approved'").fetchone()[0] == 0


def test_restricted_html_is_never_requested(client, monkeypatch):
    calls = install_fetch(monkeypatch)
    result = asyncio.run(official_monitoring.sync_official_sources())
    assert all(item['status'] == 'paused' for item in result['sources'][:3])
    assert all('ipos.gov.sg' not in address for address, _ in calls)
    assert all(alert['source'] == 'IPOS / data.gov.sg 开放数据' for alert in official_monitoring.official_alerts())


def test_watches_are_private_and_detect_changes_not_first_seen_as_new_application(client, monkeypatch):
    install_fetch(monkeypatch)
    owner, owner_id = guest(client)
    stranger, stranger_id = guest(client)
    client.get('/api/trademarks/search?q=Asterloom', headers=owner)
    assert client.post('/api/trademarks/TEST001/watch', headers=owner).status_code == 200
    assert client.get('/api/trademarks/watches', headers=stranger).json()['data'] == []
    assert len(public_data.watched_trademarks(owner_id)) == 1
    assert public_data.watched_trademarks(stranger_id) == []
    install_fetch(monkeypatch, rows=[{**ROW, 'markStatus': 'Removed'}])
    assert asyncio.run(public_data.sync_watched_trademarks())['count'] == 1
    assert any('数据变更' in alert['status'] for alert in public_data.public_trademark_alerts(owner_id))
    assert not any('数据变更' in alert['status'] for alert in public_data.public_trademark_alerts(stranger_id))
    assert client.delete('/api/trademarks/TEST001/watch', headers=stranger).status_code == 200
    assert len(public_data.watched_trademarks(owner_id)) == 1
    assert client.delete('/api/trademarks/TEST001/watch', headers=owner).status_code == 200
    assert public_data.watched_trademarks(owner_id) == []


def test_incorrect_watched_record_keeps_original(client, monkeypatch):
    install_fetch(monkeypatch)
    asyncio.run(public_data.search_public_trademarks('Asterloom'))
    public_data.watch_trademark('owner', 'TEST001')
    install_fetch(monkeypatch, rows=[], total=0)
    assert asyncio.run(public_data.sync_watched_trademarks())['status'] == 'error'
    assert public_data.watched_trademarks('owner')[0]['status'] == 'Registered'


def test_ai_translation_is_anchored_to_original_fields(client, monkeypatch):
    install_fetch(monkeypatch)
    asyncio.run(public_data.search_public_trademarks('Asterloom'))
    monkeypatch.setattr(settings, 'MODEL_PROVIDER', 'deepseek')
    monkeypatch.setattr(settings, 'DEEPSEEK_API_KEY', 'unit-test-key')
    async def complete(self, messages):
        assert json.loads(messages[1]['content'])['status'] == 'Registered'
        return json.dumps({'translations': [{'field': 'status', 'original': 'Registered', 'chinese': '已注册'}]})
    monkeypatch.setattr(ModelClient, 'complete', complete)
    result = asyncio.run(explain_public_record('TEST001'))
    assert result['aiStatus'] == 'translated'
    assert result['provider'] == 'deepseek'
    assert result['reviewRequired'] is True
    assert result['record']['status'] == 'Registered'


def test_fenced_json_translation_is_verified_and_cached(client, monkeypatch):
    install_fetch(monkeypatch)
    asyncio.run(public_data.search_public_trademarks('Asterloom'))
    monkeypatch.setattr(settings, 'MODEL_PROVIDER', 'deepseek')
    monkeypatch.setattr(settings, 'DEEPSEEK_API_KEY', 'unit-test-key')
    calls = []
    async def complete(self, messages):
        calls.append(messages)
        return '```json\n' + json.dumps({'translations': [{'field': 'status', 'original': 'Registered', 'chinese': '已注册'}]}) + '\n```'
    monkeypatch.setattr(ModelClient, 'complete', complete)
    assert asyncio.run(explain_public_record('TEST001'))['aiStatus'] == 'translated'
    assert asyncio.run(explain_public_record('TEST001'))['aiCached'] is True
    assert len(calls) == 1


def test_public_translation_falls_back_to_glm_without_changing_assistant(client, monkeypatch):
    install_fetch(monkeypatch)
    asyncio.run(public_data.search_public_trademarks('Asterloom'))
    monkeypatch.setattr(settings, 'MODEL_PROVIDER', 'glm')
    monkeypatch.setattr(settings, 'GLM_API_KEY', 'unit-test-glm-key')
    monkeypatch.setattr(settings, 'DEEPSEEK_API_KEY', 'unit-test-deepseek-key')
    calls = []
    async def complete(self, messages):
        calls.append(self.provider)
        if self.provider == 'deepseek':
            raise public_data_ai.IFLYTEKServiceError('unavailable')
        return json.dumps({'translations': [{'field': 'status', 'original': 'Registered', 'chinese': '已注册'}]})
    monkeypatch.setattr(ModelClient, 'complete', complete)
    result = asyncio.run(explain_public_record('TEST001'))
    assert calls == ['deepseek', 'glm']
    assert result['provider'] == 'glm'
    assert result['aiStatus'] == 'translated'
    assert settings.model_provider == 'glm'
    assert client.get('/api/health').json()['aiTasks']['publicDataTranslation']['fallback'] == ['glm']


def test_ai_translation_limit_retains_original_facts(client, monkeypatch):
    install_fetch(monkeypatch)
    asyncio.run(public_data.search_public_trademarks('Asterloom'))
    monkeypatch.setattr(settings, 'MODEL_PROVIDER', 'deepseek')
    monkeypatch.setattr(settings, 'DEEPSEEK_API_KEY', 'unit-test-key')
    with _connect() as connection:
        connection.execute('CREATE TABLE public_ai_requests (request_id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, provider TEXT NOT NULL)')
        for index in range(20):
            connection.execute('INSERT INTO public_ai_requests (created_at, provider) VALUES (?, ?)', (public_data._now(), 'deepseek'))
    result = asyncio.run(explain_public_record('TEST001'))
    assert result['aiStatus'] == 'unavailable'
    assert result['record']['status'] == 'Registered'
    assert '保护限额' in result['message']


@pytest.mark.parametrize('translation', [
    {'field': 'law', 'original': 'Article 8', 'chinese': '允许注册'},
    {'field': 'status', 'original': 'Pending', 'chinese': '待审'},
    {'field': 'status', 'original': 'Registered', 'chinese': '保证无风险'},
])
def test_ai_invalid_or_legal_inferences_are_discarded(client, monkeypatch, translation):
    install_fetch(monkeypatch)
    asyncio.run(public_data.search_public_trademarks('Asterloom'))
    monkeypatch.setattr(settings, 'MODEL_PROVIDER', 'deepseek')
    monkeypatch.setattr(settings, 'DEEPSEEK_API_KEY', 'unit-test-key')
    async def complete(self, messages):
        return json.dumps({'translations': [translation]})
    monkeypatch.setattr(ModelClient, 'complete', complete)
    result = asyncio.run(explain_public_record('TEST001'))
    assert result['aiStatus'] == 'unavailable'
    assert result['translations'] == []


def test_assistant_public_lookup_does_not_become_approved_legal_answer(client, monkeypatch):
    install_fetch(monkeypatch)
    response = asyncio.run(AssistantOrchestrator().answer(AssistantChatRequest(question='新加坡商标数据查询：Asterloom'), 'public-user'))
    assert response.answer_status == 'public_data_reference'
    assert response.sources[0].source_type == 'official_open_dataset'
    assert 'TEST001' in response.answer
    assert '不是法律近似检索' in response.answer


def test_http_fetch_obeys_limits_and_never_redirects(client, monkeypatch):
    original = httpx.AsyncClient
    def reply(request):
        return httpx.Response(429, json={'error': 'rate limited'})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **options: original(transport=httpx.MockTransport(reply), **options))
    with pytest.raises(public_data.PublicDataError, match='限流'):
        asyncio.run(public_data._fetch_json(public_data.API_URL))


def test_endpoints_require_auth_and_missing_record_does_not_call_ai(client):
    assert client.get('/api/trademarks/search?q=Asterloom').status_code == 401
    assert client.get('/api/trademarks/watches').status_code == 401
    headers, _ = guest(client)
    assert client.post('/api/trademarks/not-found/explain', headers=headers).status_code == 404


def configuration_script():
    location = Path(__file__).resolve().parents[2] / 'scripts/configure_deepseek.py'
    spec = importlib.util.spec_from_file_location('safe_deepseek_configuration', location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_private_config_update_preserves_glm_as_primary():
    module = configuration_script()
    original = "GLM_API_KEY='keep-private'\nMODEL_PROVIDER='glm'\nDEEPSEEK_API_KEY='old'\n"
    updated = module.updated_environment(original, 'new-test-key')
    assert "GLM_API_KEY='keep-private'" in updated
    assert updated.count('MODEL_PROVIDER=') == 1
    assert "MODEL_PROVIDER='glm'" in updated
    assert 'old' not in updated


def test_private_config_uses_verified_flash_model():
    module = configuration_script()
    updated = module.updated_environment("GLM_API_KEY='keep-private'\n", 'new-test-key', 'deepseek-v4-flash')
    assert "DEEPSEEK_MODEL='deepseek-v4-flash'" in updated


def test_key_setup_checks_official_api_and_never_returns_key(monkeypatch, tmp_path):
    module = configuration_script()
    monkeypatch.setattr(module, 'PROJECT', tmp_path)
    environment = tmp_path / 'backend/.env'
    environment.parent.mkdir()
    (environment.parent / 'data').mkdir()
    environment.write_text("GLM_API_KEY='keep-existing'\nMODEL_PROVIDER='glm'\n")
    monkeypatch.setattr(module, 'ENVIRONMENT', environment)
    monkeypatch.setattr(module.time, 'sleep', lambda duration: None)
    monkeypatch.setattr(module.subprocess, 'run', lambda *args, **kwargs: None)
    seen = []
    def reply(request):
        seen.append(request)
        if request.url.path == '/models':
            return httpx.Response(200, json={'data': [{'id': 'deepseek-flash'}]})
        if request.url.path == '/chat/completions':
            return httpx.Response(200, json={'choices': [{'message': {'content': 'OK'}}]})
        return httpx.Response(200, json={'aiProvider': 'glm', 'aiModel': 'glm-4-flash', 'aiStatus': 'configured', 'aiTasks': {'publicDataTranslation': {'provider': 'deepseek', 'model': 'deepseek-flash'}}})
    original = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **options: original(transport=httpx.MockTransport(reply), **options))
    key = 'sk-unit-test-not-a-real-secret'
    message = module.configure(key)
    assert key not in message
    assert all(request.url.host == 'api.deepseek.com' and request.url.scheme == 'https' for request in seen[:2])
    assert 'Authorization' not in seen[2].headers
    assert environment.stat().st_mode & 0o777 == 0o600
    assert "GLM_API_KEY='keep-existing'" in environment.read_text()
    assert "MODEL_PROVIDER='glm'" in environment.read_text()
    assert key not in (environment.parent / 'data/deepseek-configuration.json').read_text()


def test_key_validation_calls_discovered_flash_model(monkeypatch):
    module = configuration_script()
    seen = []
    def reply(request):
        seen.append(request)
        if request.url.path == '/models':
            return httpx.Response(200, json={'data': [{'id': 'deepseek-v4-flash'}]})
        return httpx.Response(200, json={'choices': [{'message': {'content': 'OK'}}]})
    original = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **options: original(transport=httpx.MockTransport(reply), **options))
    assert module.validate_key('sk-unit-test-not-a-real-secret') == 'deepseek-v4-flash'
    assert json.loads(seen[1].content)['model'] == 'deepseek-v4-flash'
    assert 'thinking' not in json.loads(seen[1].content)


def test_key_validation_prefers_current_flash_api_name(monkeypatch):
    module = configuration_script()
    seen = []
    def reply(request):
        seen.append(request)
        if request.url.path == '/models':
            return httpx.Response(200, json={'data': [{'id': 'deepseek-v4-flash'}, {'id': 'deepseek-flash'}]})
        return httpx.Response(200, json={'choices': [{'message': {'content': 'OK'}}]})
    original = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **options: original(transport=httpx.MockTransport(reply), **options))
    assert module.validate_key('sk-unit-test-not-a-real-secret') == 'deepseek-flash'
    assert json.loads(seen[1].content)['model'] == 'deepseek-flash'


def test_key_validation_accepts_vflash_only_when_official_list_returns_it(monkeypatch):
    module = configuration_script()
    seen = []
    def reply(request):
        seen.append(request)
        if request.url.path == '/models':
            return httpx.Response(200, json={'data': [{'id': 'deepseek-vflash'}]})
        return httpx.Response(200, json={'choices': [{'message': {'content': 'OK'}}]})
    original = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **options: original(transport=httpx.MockTransport(reply), **options))
    assert module.validate_key('sk-unit-test-not-a-real-secret') == 'deepseek-vflash'
    assert json.loads(seen[1].content)['model'] == 'deepseek-vflash'


def test_key_validation_explains_official_http_failure_without_leaking_key(monkeypatch):
    module = configuration_script()
    def reply(request):
        if request.url.path == '/models':
            return httpx.Response(200, json={'data': [{'id': 'deepseek-flash'}]})
        return httpx.Response(402, json={'error': {'message': 'secret'}})
    original = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **options: original(transport=httpx.MockTransport(reply), **options))
    with pytest.raises(ValueError, match='HTTP 402（账户余额不足）') as failure:
        module.validate_key('sk-unit-test-not-a-real-secret')
    assert 'secret' not in str(failure.value)


def test_key_validation_retries_transient_model_list_failure(monkeypatch):
    module = configuration_script()
    calls = []
    def reply(request):
        calls.append(request)
        if request.url.path == '/models' and len(calls) == 1:
            raise httpx.ConnectError('temporary failure')
        if request.url.path == '/models':
            return httpx.Response(200, json={'data': [{'id': 'deepseek-flash'}]})
        return httpx.Response(200, json={'choices': [{'message': {'content': 'OK'}}]})
    original = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **options: original(transport=httpx.MockTransport(reply), **options))
    monkeypatch.setattr(module.time, 'sleep', lambda duration: None)
    assert module.validate_key('sk-unit-test-not-a-real-secret') == 'deepseek-flash'
    assert len(calls) == 3


def test_key_validation_reports_network_stage_without_leaking_key(monkeypatch):
    module = configuration_script()
    def reply(request):
        if request.url.path == '/models':
            return httpx.Response(200, json={'data': [{'id': 'deepseek-flash'}]})
        raise httpx.ReadError('secret')
    original = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **options: original(transport=httpx.MockTransport(reply), **options))
    with pytest.raises(ValueError, match='模型调用网络连接失败（ReadError）') as failure:
        module.validate_key('sk-unit-test-not-a-real-secret')
    assert 'secret' not in str(failure.value)


def test_key_validation_ignores_shell_proxy_settings(monkeypatch):
    module = configuration_script()
    options_seen = []
    def reply(request):
        if request.url.path == '/models':
            return httpx.Response(200, json={'data': [{'id': 'deepseek-flash'}]})
        return httpx.Response(200, json={'choices': [{'message': {'content': 'OK'}}]})
    original = httpx.Client
    def client(**options):
        options_seen.append(options)
        return original(transport=httpx.MockTransport(reply), **options)
    monkeypatch.setattr(module.httpx, 'Client', client)
    monkeypatch.setenv('HTTPS_PROXY', 'http://127.0.0.1:1')
    assert module.validate_key('sk-unit-test-not-a-real-secret') == 'deepseek-flash'
    assert options_seen[0]['trust_env'] is False


def test_key_setup_rolls_back_if_service_cannot_switch(monkeypatch, tmp_path):
    module = configuration_script()
    environment = tmp_path / '.env'
    original = "GLM_API_KEY='keep-existing'\nMODEL_PROVIDER='glm'\n"
    environment.write_text(original)
    monkeypatch.setattr(module, 'ENVIRONMENT', environment)
    monkeypatch.setattr(module, 'validate_key', lambda key: 'deepseek-flash')
    calls = []
    def restart(*args, **kwargs):
        calls.append(kwargs.get('check'))
        if kwargs.get('check'):
            raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(module.subprocess, 'run', restart)
    with pytest.raises(ValueError, match='恢复原配置'):
        module.configure('sk-unit-test-not-a-real-secret')
    assert environment.read_text() == original
    assert calls == [True, False]


def test_key_setup_rejects_shell_and_env_injection_before_network():
    module = configuration_script()
    with pytest.raises(ValueError, match='格式'):
        module.validate_key("sk-injected'\nMODEL_PROVIDER=other")
