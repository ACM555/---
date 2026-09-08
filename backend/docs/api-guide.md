# Outbound-Guard API 接口文档

本文档用于前后端与法学队友联调确认。Pydantic 模型位于 `app/models/audit.py`，是接口字段契约的唯一真相来源。

## 基本信息

| 项目 | 说明 |
|---|---|
| Base URL | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| API 版本 | `1.0.0` |
| 统一响应 | `{ "code": number, "message": string, "data": object | null }` |

## 接口列表

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| POST | `/api/audit` | 提交商标审查 |
| GET | `/api/audit/result/{taskId}` | 轮询审查结果 |

## 1. GET /api/health — 健康检查

用途：前端启动时探测后端可用性。

示例响应：

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

## 2. POST /api/audit — 提交商标审查

用途：提交品牌信息和 Logo，启动 AI 合规审查。后端立即返回 `taskId`，前端用它轮询结果。

请求体模型：`AuditRequest`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| brandName | string | 是 | 品牌名称，最大 50 字符 |
| englishName | string | 否 | 品牌英文名称，最大 100 字符 |
| niceClass | string | 是 | 尼斯分类，如 `第43类-餐饮服务` |
| goodsServices | string | 是 | 商品/服务描述，品牌主营业务和目标市场 |
| logo | string(Base64) | 是 | Logo 图片 Base64 字符串，不含 `data:image` 前缀 |

示例请求：

```http
POST /api/audit
Content-Type: application/json
```

```json
{
  "brandName": "墨兰奶白",
  "englishName": "Moc Lan",
  "niceClass": "第43类-餐饮服务",
  "goodsServices": "新茶饮品牌，主营奶茶饮品，目标市场越南",
  "logo": "<base64-string-without-prefix>"
}
```

示例响应：

```json
{
  "code": 0,
  "message": "审查已提交",
  "data": {
    "taskId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "pending",
    "message": "审查已提交，正在处理中"
  }
}
```

curl 示例：

```bash
curl -X POST "http://localhost:8000/api/audit" \
  -H "Content-Type: application/json" \
  -d '{
    "brandName": "墨兰奶白",
    "englishName": "Moc Lan",
    "niceClass": "第43类-餐饮服务",
    "goodsServices": "新茶饮品牌，主营奶茶饮品，目标市场越南",
    "logo": "abc123"
  }'
```

## 3. GET /api/audit/result/{taskId} — 获取审查结果

用途：轮询审查结果。模拟阶段后端按任务创建时间推进状态，4 秒后返回完整“墨兰奶白”测试报告。

路径参数：

| 字段 | 类型 | 说明 |
|---|---|---|
| taskId | string(UUID) | `POST /api/audit` 返回的审查任务 ID |

状态流转时间线：

| 时间 | status | currentStep | progress |
|---|---|---:|---:|
| 0-1s | pending | 0 | 10 |
| 1-2s | processing | 0 | 33 |
| 2-3s | processing | 1 | 66 |
| 3-4s | processing | 2 | 90 |
| 4s+ | done | 2 | 100 |

步骤含义：

| currentStep | 含义 |
|---:|---|
| 0 | 法条规则匹配 |
| 1 | 多模态视觉比对 |
| 2 | 风险综合评估 |

处理中响应示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "taskId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "processing",
    "currentStep": 1,
    "progress": 66
  }
}
```

完成响应示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "taskId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "done",
    "currentStep": 2,
    "progress": 100,
    "brandName": "墨兰奶白",
    "niceClass": "第43类-餐饮服务",
    "goodsServices": "新茶饮品牌，主营奶茶饮品，目标市场越南",
    "riskLevel": "high",
    "riskScore": 82,
    "overallResult": "存在跨类目驰名商誉攀附风险，建议暂缓提交。",
    "hitRules": [
      {
        "ruleType": "relative",
        "article": "越南《工业产权法》第74.2(c)条",
        "content": "与在越南已注册的驰名商标构成混淆性近似",
        "applicable": true,
        "similarityType": "图形相似-四叶花卉几何结构",
        "similarityScore": 87,
        "note": "上传商标四叶花卉图形与Louis Vuitton在越全类注册的几何特征高度近似"
      }
    ],
    "references": [
      {
        "refType": "trademark",
        "title": "Louis Vuitton",
        "source": "WIPO Madrid Monitor",
        "date": "2019-03-15",
        "registrationNo": "4VN-2019-00XXX",
        "summary": "全类注册（含第43类餐饮服务）",
        "relevance": "本案品牌四叶草图形与其注册图形在几何构图上高度近似"
      }
    ],
    "suggestions": [
      {
        "priority": "P0",
        "title": "立即停止使用四叶花卉图形",
        "description": "在越南市场投放、门店物料、社媒内容及线上店铺中暂停使用当前图形。"
      }
    ],
    "manualReviewRequired": true
  }
}
```

任务不存在响应：

```json
{
  "code": 404,
  "message": "任务不存在",
  "data": null
}
```

curl 示例：

```bash
curl "http://localhost:8000/api/audit/result/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

## 字段说明

### 统一字段（9 项）

| 字段 | 类型 | 来源 | 说明 |
|---|---|---|---|
| brandName | string | 用户输入/后端返回 | 品牌名称 |
| niceClass | string | 用户选择/后端返回 | 尼斯分类 |
| goodsServices | string | 用户输入/后端返回 | 商品/服务描述 |
| logo | string(Base64) | 用户上传后前端转换 | Logo 图片 Base64 字符串 |
| riskLevel | enum | 后端返回 | 风险等级：`high` / `medium` / `low` |
| hitRules | array | 后端返回 | 命中规则列表，合并绝对驳回与相对驳回 |
| references | array | 后端返回/本地知识库 | 引用依据列表，合并法条、判例、商标记录 |
| suggestions | array | 后端返回 | 合规建议列表，对应前端法律建议 |
| manualReviewRequired | boolean | 后端返回 | 是否需要人工复核 |

### hitRules 子结构

| 字段 | 类型 | 说明 |
|---|---|---|
| ruleType | enum | `absolute` / `relative` |
| article | string | 法条编号 |
| content | string | 法条内容摘要 |
| applicable | boolean | 是否适用/触发 |
| similarityType | string | 相似类型 |
| similarityScore | number | 相似度评分 0-100 |
| note | string | 审查说明 |

### references 子结构

| 字段 | 类型 | 说明 |
|---|---|---|
| refType | enum | `law` / `case` / `trademark` |
| title | string | 标题/案件名/品牌名 |
| source | string | 来源 |
| date | string | 日期，建议 `YYYY-MM-DD` |
| registrationNo | string | 注册号，商标记录使用 |
| summary | string | 摘要/判决摘要 |
| relevance | string | 与本案关联性说明 |

### suggestions 子结构

| 字段 | 类型 | 说明 |
|---|---|---|
| priority | enum | `P0` / `P1` / `P2` |
| title | string | 建议标题 |
| description | string | 建议详细描述 |

## 前端联调指南

### Vite Proxy 配置

建议在前端 `vite.config.ts` 中配置：

```ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

### 启动顺序

1. 启动后端：

```powershell
cd "E:\codex项目\本地电脑\西南政法智能体大赛\outbound-guard-backend"
.\venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

2. 启动前端：

```powershell
cd "E:\codex项目\本地电脑\西南政法智能体大赛\outbound-guard"
npm.cmd run dev
```

3. 访问：

```text
http://localhost:5173
```

### 轮询逻辑

| 动作 | 前端行为 |
|---|---|
| 提交表单 | `POST /api/audit`，获取 `taskId` |
| 审查中 | 每 2 秒 `GET /api/audit/result/{taskId}` |
| 处理中 | 根据 `currentStep` 高亮步骤，根据 `progress` 展示进度 |
| 完成 | `status=done` 后停止轮询，渲染报告 |
| 超时 | 60 秒未完成，停止轮询并提示用户 |
| 失败 | `status=error` 或 `code !== 0` 时展示错误信息 |

### 前端联调 Checklist

- 后端 `http://localhost:8000/api/health` 返回 `status=ok`
- 前端 Vite proxy 已配置 `/api -> http://localhost:8000`
- CORS 环境变量 `CORS_ORIGINS` 包含 `http://localhost:5173`
- 表单提交字段为 `brandName`、`englishName`、`niceClass`、`goodsServices`、`logo`
- `logo` 不包含 `data:image/png;base64,` 前缀
- 轮询间隔为 2 秒
- 轮询超时时间为 60 秒
- `code !== 0` 时弹出错误提示
- `status=done` 后将 `data` 映射到报告页

## 错误码说明

| 场景 | HTTP 状态 | code | 说明 |
|---|---:|---:|---|
| 请求体缺少必填字段 | 422 | FastAPI 默认 | Pydantic 校验失败 |
| 任务不存在 | 200 | 404 | 业务层表示 taskId 未命中 |
| 正常提交/查询 | 200 | 0 | 成功 |

