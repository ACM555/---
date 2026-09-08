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

真实 `IFLYTEK_API_PASSWORD` 只能通过本机 `.env` 提供，禁止写入源码、前端、文档或交付包。X2 HTTP 使用 `IFLYTEK_BASE_URL=https://spark-api-open.xf-yun.com/x2` 和 `IFLYTEK_MODEL=spark-x`。

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
