# Agent API 文档

## 概述

Agent API 是为 Prometheus Agent 提供的专用接口，用于自动化触发健康管理系统的核心功能。

## 认证

所有 Agent API 端点都需要通过 `X-Agent-API-Key` Header 进行认证：

```
X-Agent-API-Key: prometheus-agent-key-2026
```

## API 端点

### 1. 同步 Garmin 数据

**端点**: `POST /api/v1/agent/sync-data`

**描述**: 同步指定用户或所有用户的 Garmin 健康数据

**请求体**:
```json
{
  "user_id": 1,  // 可选，不传则同步所有用户
  "days": 7      // 可选，默认为 1 天
}
```

**响应示例**:
```json
{
  "success": true,
  "user_id": 1,
  "days_synced": 1,
  "metrics_created": 0,
  "metrics_updated": 1,
  "errors": []
}
```

---

### 2. 生成健康报告

**端点**: `POST /api/v1/agent/generate-report`

**描述**: 为指定用户生成早报或晚报

**请求体**:
```json
{
  "user_id": 1,
  "report_type": "morning",  // 或 "evening"
  "report_date": "2026-03-23"  // 可选，默认为今天
}
```

**响应示例**:
```json
{
  "success": true,
  "user_id": 1,
  "report_type": "morning",
  "report_date": "2026-03-23",
  "content": "# 晨间报告...",
  "errors": []
}
```

---

### 3. 发送邮件通知

**端点**: `POST /api/v1/agent/send-email`

**描述**: 发送健康报告邮件通知

**请求体**:
```json
{
  "user_id": 1,
  "report_type": "morning",
  "custom_content": "自定义内容"  // 可选，不传则使用数据库中的报告
}
```

**响应示例**:
```json
{
  "success": true,
  "user_id": 1,
  "message": "Email sent successfully",
  "errors": []
}
```

---

### 4. 早报工作流

**端点**: `POST /api/v1/agent/morning-workflow`

**描述**: 一键执行完整的早报流程（同步 + 生成 + 发送）

**请求体**:
```json
{
  "user_ids": [1, 2]  // 可选，不传则执行所有用户
}
```

**响应示例**:
```json
{
  "success": true,
  "results": {
    "sync": [
      {
        "success": true,
        "user_id": 1,
        "days_synced": 1,
        "metrics_created": 0,
        "metrics_updated": 1,
        "errors": []
      }
    ],
    "reports": [
      {
        "success": true,
        "user_id": 1,
        "report_type": "morning",
        "report_date": "2026-03-23",
        "content": "# 晨间报告...",
        "errors": []
      }
    ],
    "emails": [
      {
        "success": true,
        "user_id": 1,
        "message": "Email sent successfully",
        "errors": []
      }
    ],
    "errors": []
  },
  "errors": []
}
```

---

### 5. 晚报工作流

**端点**: `POST /api/v1/agent/evening-workflow`

**描述**: 一键执行完整的晚报流程（同步 + 生成 + 发送）

**请求体**:
```json
{
  "user_ids": [1, 2]  // 可选，不传则执行所有用户
}
```

**响应示例**: 与早报工作流相同

---

## 使用示例

### cURL

```bash
# 同步数据
curl -X POST "http://localhost:8000/api/v1/agent/sync-data" \
  -H "X-Agent-API-Key: prometheus-agent-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "days": 1}'

# 生成报告
curl -X POST "http://localhost:8000/api/v1/agent/generate-report" \
  -H "X-Agent-API-Key: prometheus-agent-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "report_type": "morning"}'

# 发送邮件
curl -X POST "http://localhost:8000/api/v1/agent/send-email" \
  -H "X-Agent-API-Key: prometheus-agent-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "report_type": "morning"}'

# 早报工作流
curl -X POST "http://localhost:8000/api/v1/agent/morning-workflow" \
  -H "X-Agent-API-Key: prometheus-agent-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"user_ids": [1, 2]}'

# 晚报工作流
curl -X POST "http://localhost:8000/api/v1/agent/evening-workflow" \
  -H "X-Agent-API-Key: prometheus-agent-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"user_ids": [1, 2]}'
```

### PowerShell

```powershell
$headers = @{
    "X-Agent-API-Key" = "prometheus-agent-key-2026"
    "Content-Type" = "application/json"
}

# 同步数据
$body = @{
    user_id = 1
    days = 1
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/agent/sync-data" -Method POST -Headers $headers -Body $body
$response | ConvertTo-Json -Depth 10

# 早报工作流
$body = @{
    user_ids = @(1, 2)
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/agent/morning-workflow" -Method POST -Headers $headers -Body $body
$response | ConvertTo-Json -Depth 10
```

---

## 错误处理

所有 API 端点在失败时都会返回详细的错误信息：

```json
{
  "success": false,
  "errors": ["错误详情1", "错误详情2"]
}
```

常见错误：
- `401 Unauthorized`: API Key 缺失或无效
- `403 Forbidden`: API Key 不正确
- `500 Internal Server Error`: 服务器内部错误（查看 errors 数组）

---

## 注意事项

1. **API Key 安全**: 请妥善保管 API Key，不要在生产环境中暴露
2. **数据同步**: 建议在生成报告前先同步数据
3. **邮件配置**: 发送邮件前需要配置 SMTP 服务器
4. **智谱 AI**: 生成报告需要配置 `ZHIPU_API_KEY`
5. **报告重复**: 重新生成报告会覆盖旧报告

---

## 定时任务建议

### 早报
- 建议时间: 每天 07:00-09:00
- 调用端点: `/api/v1/agent/morning-workflow`

### 晚报
- 建议时间: 每天 20:00-22:00
- 调用端点: `/api/v1/agent/evening-workflow`

---

## 技术实现

- **框架**: FastAPI
- **认证**: 自定义 API Key 认证
- **数据模型**: Pydantic
- **数据库**: SQLite (SQLAlchemy ORM)
- **AI**: 智谱 GLM-4

---

## 更新日志

### v1.0.0 (2026-03-23)
- 初始版本发布
- 实现所有核心功能
- 添加完整的错误处理
- 支持批量操作
