# 出海卫士：东盟跨境商事法律 AI 助手

面向中国企业进入东盟市场的受控法律资料检索与风险提示系统，覆盖 M1–M6 六个业务模块。系统仅基于已审核、可回查资料提供初步参考、待补事实与人工复核提示，不构成律师法律意见、主管机关决定或结果保证。

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
npm run test:e2e
npm run build

cd backend
.\venv\Scripts\python.exe -m unittest
```

端到端测试会联调真实 Vite 与 FastAPI 服务。交付演示见 `比赛演示脚本_P6.md`，交付清单见 `P6_交付清单与验收记录.md`。真实密钥不得写入源码、页面、文档或交付包。
