# 出海卫士：东盟跨境商事法律 AI 助手

面向中国企业进入东盟市场的受控法律资料检索与风险提示系统，覆盖 M1–M6 六个业务模块。系统仅基于已审核、可回查资料提供初步参考、待补事实与人工复核提示，不构成律师法律意见、主管机关决定或结果保证。

## 扫码体验

- 东盟体验入口：<http://154.40.45.149/asean-legal/#/experience>，使用标准 HTTP 80 端口，点击“开始体验”创建独立的普通游客会话，无需注册，不授予管理员权限。
- 二维码图片：<http://154.40.45.149/asean-legal/teacher-experience-qr.png>，登录页支持扫码、直接打开和下载二维码。
- 演示账号：在 `backend/.env` 配置 `DEMO_MODE=true`、`DEMO_USERNAME`、`DEMO_PASSWORD` 后，后端启动时自动创建该账号（普通用户权限，不是管理员，不覆盖同名账号）。账号名与密码仅保存在本机 `.env`，不写入源码、文档或交付包。`DEMO_MODE` 开启但用户名或密码缺失时启动即报错，避免配置了却登录不上。
- 只保留上述标准端口入口，旧 `39013` 公网入口已停用。后端仅监听 `127.0.0.1:39013`，供本机反向代理使用。子路径部署的 API 自动使用 `/asean-legal/api`，登录状态与本地审查记录按部署前缀隔离，不与越南商标项目混用。
- 重新生成并校验二维码：`backend/.venv/bin/python scripts/generate_teacher_qr.py`。更换部署地址时同步更新脚本中的 `EXPERIENCE_URL`，再构建前端。
- 页面打不开但健康接口正常时，访问 <http://154.40.45.149/asean-legal/connection-check.html>。诊断在当前浏览器检查脚本、样式、本地存储与实际页面启动，不创建游客账号、不上传检查结果。启动失败时页面也提供诊断链接与错误提示。

标准端口入口由 `/root/openclaw-https-proxy/proxy.mjs` 将 `/asean-legal/` 请求转发到本机 `39013`，并移除此前缀；改动后执行 `node --check /root/openclaw-https-proxy/proxy.mjs`，再重启 `openclaw-https-proxy.service`。SSH 仍使用 22 端口，本机代理分流规则需在用户的 Clash 客户端修改。

## 启动后端

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# 仅在本机 .env 配置管理员密码与讯飞 HTTP APIPassword
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

## 启动前端

```powershell
npm ci
npm run dev -- --host 127.0.0.1
```

- 前端：<http://127.0.0.1:5173/>
- 后端接口文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/health>

## 测试与构建

```powershell
npm test
npm run test:backend
npm run test:e2e
npm run build

cd backend
.\venv\Scripts\python.exe -m unittest
```

后端测试使用临时数据库、上传、报告与资料目录，并显式禁用真实模型密钥；浏览器测试仅使用独立的测试后端，不访问生产数据库。端到端测试会联调真实 Vite 与 FastAPI 服务，覆盖注册登录、游客权限、六模块筛查、资料筛选、后台审核、报告及 PDF。

RAG 请求识别回归：`npm run test:backend -- backend/tests/test_assistant_request_understanding.py`。普通提问不再因“我们公司”误入 M1；明确的 M1–M6 编号优先，同一用户、同一会话的明确追问可沿用国家与模块，多国或多模块问题要求拆分，不混用资料。中文上传资料按片段匹配，作为当前用户的待核验业务背景传入模型，不进入已审核法律来源列表，也不能绕过法律资料审核。缺少已审核资料时会显示已识别范围与缺失原因；测试通过不代表生产资料已审核或真实模型调用已验证。

已完成的商标审查会自动进入当前用户的品牌资产库和报告中心，支持查看与下载。没有真实在先权利证据时，报告显示“待核验”，图形复杂度和对称性不计作法律风险；内部筛查规则与官方原文回查入口分开标注。生成、修改、归档与最近查看时间分别保存，查看报告不会改写归档时间。

监控中心改为使用 IPOS 在 data.gov.sg 发布的商标申请开放数据 API，许可为 Singapore Open Data Licence，页面保留官方来源和许可归属说明。IPOS 普通网页因缓存/提取条款限制暂停自动采集，历史网页索引不继续展示。支持真实文字字段关键词检索、分页、申请号/状态/类别/原始日期、逐项 AI 辅助翻译和用户隔离的关注列表。首次收录不是新申请，字段变化不自动视为法律风险；无结果不表示没有在先权利。接口报告计数也不代表完整实时注册库覆盖度。

生产环境在 `backend/.env` 配置 `MONITORING_ENABLED=true` 可启用定时采集，`MONITORING_INTERVAL_SECONDS=21600` 为每 6 小时一次，最短允许 1 小时。每轮核对数据集元数据和 25 条基线，并按申请号复查关注记录；每用户最多 10 条，系统最多 30 个不同申请号。请求间隔至少 3 秒，遇到 403/429 不绕过，按需查询缓存 6 小时。管理员可调用 `POST /api/monitoring/sync` 手动采集，普通用户不可触发。开放 API 无 Key 时支持低额度访问，可选 `PUBLIC_DATA_API_KEY` 提高合法额度；这与模型 Key 是两类独立凭据。

双模型协作时在服务端私有 `.env` 保持 `MODEL_PROVIDER=glm` 和有效的 `GLM_API_KEY`，另配置 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL=https://api.deepseek.com`、`DEEPSEEK_MODEL=deepseek-flash` 后重启服务。官方文档将 `deepseek-flash` 作为 DeepSeek-V4.1-Flash 的 API 模型名；`deepseek-v4-flash` 是仍可用的旧别名。若账户的官方 `/models` 接口实际列出 `deepseek-vflash` 等其他 Flash 名称，配置脚本只会在该名称通过真实调用后采用，不凭名称猜测。正式法律助手使用 GLM；公开商标字段辅助翻译优先 DeepSeek Flash，调用失败或结果不合格时回退 GLM。`/api/health` 的 `aiTasks` 可查看任务分工；它只表示配置状态，不代替真实模型连通性验证。

安全输入支持 `backend/.venv/bin/python scripts/configure_deepseek.py` 的终端隐藏输入，或加 `--serve` 启动仅监听 `127.0.0.1:39014` 的一次性网页表单（1 小时过期）。远程操作先在自己电脑执行 `ssh -N -L 39014:127.0.0.1:39014 root@154.40.45.149`，再打开脚本打印的本机地址。不得把该端口转发到公网，或在现有公开 HTTP 网站输入 Key。脚本向官方认证、做一次极小调用后才以权限 600 原子保存并启用双模型分工；失败保留/恢复原配置。密钥不进入浏览器持久存储、日志、SQLite 或交付文件。

无需 SSH 的临时配置入口可由 `scripts/public_deepseek_portal.py --hostname <临时 HTTPS 域名>` 提供，需通过有效 HTTPS 反向隧道访问。页面使用临时 RSA 公钥在浏览器端加密 Key，仅接受指定域名及同源提交；入口一小时后关闭。该脚本复用上述官方验证和自动回滚流程。

AI 助手可输入“新加坡商标数据查询：关键词”查询真实开放记录。该路径与正式法律 RAG 分离，回答标为 `public_data_reference`；AI 仅逐项翻译状态和商品服务，并校验原始字段，失败展示官方原文，不生成法律结论或自动批准法源。允许严格 JSON 或仅包裹该 JSON 的 Markdown 代码块，校验后的翻译缓存 1 小时，每个提供方每小时最多 20 个未缓存翻译请求，避免无上限消耗模型 Key。

M1–M6 的正式法律回答只使用审核通过的来源与摘录，候选资料不能自动成为法律回答依据。新加坡 M5 本国申请资料核对演示包提供官方指南版本、适用条件、5 项核对输出与原文定位，但仍标注待审核，不绕过正式法源审核门槛。

交付演示见 `比赛演示脚本_P6.md`，交付清单见 `P6_交付清单与验收记录.md`。真实密钥不得写入源码、页面、文档或交付包。

标准端口迁移、本轮独立品牌用例和未就绪项见 `东盟80端口验收_2026-10-13.md`。

飞书问题逐项修复、真实公告采集、主场景核对包及仍待审核项见 `飞书问题修复验收_2026-10-15.md`；二维码端不在该轮修改范围内。
