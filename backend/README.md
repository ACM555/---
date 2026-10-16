# 出海卫士后端

FastAPI 服务为六模块筛查、法律资料审核、受控问答与 M5 风险提示清单提供接口。

## Start

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## API Docs

After startup, open http://localhost:8000/docs to view Swagger UI.

AI/RAG 模型配置位于 `backend/.env`。系统按以下优先级选择模型：

1. `GLM_API_KEY` + `GLM_BASE_URL` + `GLM_MODEL`（推荐，智谱 OpenAI 兼容接口）
2. `IFLYTEK_API_PASSWORD` + `IFLYTEK_BASE_URL` + `IFLYTEK_MODEL`
3. `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL`（其他 OpenAI 兼容服务）

真实密钥只能保存在服务器本机的 `backend/.env`，禁止写入源码、前端、文档或交付包。修改后执行：

```bash
sudo systemctl restart chuhai-weishi.service
curl http://127.0.0.1:39013/api/health
```

健康检查只返回 `aiStatus`、`aiProvider` 和 `aiModel`，不会返回密钥。

## Directory Layout

```text
app/           Main application package
app/api/       Route modules, such as health.py and audit.py
app/models/    Pydantic request and response models
app/services/  Business services, rules engine, model calls, report generation
app/core/      Configuration, constants, and shared utilities
data/          Local knowledge base and trademark data
rules/         Rule definition files for deterministic screening
reports/       Generated compliance reports
uploads/       Temporary uploaded trademark images
tests/         Automated tests
```
