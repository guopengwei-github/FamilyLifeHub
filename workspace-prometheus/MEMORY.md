# MEMORY.md - Prometheus 长期记忆

---

## 🔥 核心准则（最高优先级）

### 1️⃣ 代码修改必须在 Worktree 中进行

```
❌ 禁止：直接在主仓库（main/master 分支）修改代码
❌ 禁止：让 subagent 在主仓库修改代码
✅ 必须：使用 git worktree 创建独立工作树
✅ 必须：通过 Pull Request 提交修改
✅ 必须：subagent 任务明确指定 worktree 路径
```

**违规后果**：立即回滚所有修改，在 worktree 中重新操作

**正确流程**：
```bash
# 1. 创建 worktree
git worktree add -b feature/xxx ../project_feature

# 2. 在 worktree 中操作
cd ../project_feature

# 3. 提交并创建 PR
git add . && git commit -m "feat: xxx"
git push origin feature/xxx
gh pr create --title "xxx" --body "..."
```

### 2️⃣ 配置文件修改必须获得用户许可

```
❌ 禁止：未经许可修改任何配置文件
✅ 必须：先说明 → 等待许可 → 才能修改
```

---

### 3️⃣ 报告生成流程规范

#### 晚报 Cron 任务完整流程

```
1. 获取所有活跃用户（is_active == 1）
   ↓
2. 对每个用户：
   ├─ 同步 Garmin 数据（调用 sync_garmin_data_for_user）
   │  ├─ 检查 Garmin 连接状态（sync_status == "connected"）
   │  ├─ 优先使用 OAuth tokens
   │  │  ├─ 反序列化 tokens 并验证（client.connectapi）
   │  │  └─ 成功 → 更新 sync_status = "connected"
   │  └─ 失败 → 重新登录 → 存储新 tokens
   │
   ├─ 检查同步结果
   │  ├─ 失败 → 发送 QQ 提醒 → 跳过该用户
   │  └─ 成功 → 继续下一步
   │
   ├─ 检查晚报是否已存在
   │  └─ 已存在 → 删除（db.delete）→ db.commit
   │
   ├─ 生成晚报
   │  ├─ 聚合数据（aggregate_evening_report_data）
   │  │  ├─ 心率数据（今日 + 7天平均）
   │  │  ├─ 压力分布（今日 + 7天平均）
   │  │  ├─ 身体电量消耗（早晨→当前）
   │  │  ├─ 今日活动（步数/运动/卡路里）
   │  │  └─ 静息心率
   │  ├─ 格式化提示词（format_evening_report_prompt）
   │  └─ 调用 LLM（ZhipuProvider, glm-4.7, max_tokens=8192）
   │
   ├─ 保存到数据库
   │  ├─ 创建 HealthReport 记录
   │  └─ db.add() → db.commit()
   │
   └─ 发送邮件通知
      └─ EmailService.send_report_notification()
```

#### 早报 Cron 任务完整流程

```
1. 获取所有活跃用户（is_active == 1）
   ↓
2. 对每个用户：
   ├─ 同步 Garmin 数据（调用 sync_garmin_data_for_user）
   │  ├─ 检查 Garmin 连接状态
   │  ├─ 优先使用 OAuth tokens
   │  └─ 失败 → 重新登录
   │
   ├─ 检查睡眠数据是否存在
   │  ├─ 不存在 → 发送 QQ 提醒 → 跳过该用户
   │  └─ 存在 → 继续下一步
   │
   ├─ 检查早报是否已存在
   │  └─ 已存在 → 跳过（不删除）
   │
   ├─ 生成早报
   │  ├─ 聚合数据（aggregate_morning_report_data）
   │  │  ├─ 睡眠数据（昨晚 + 7天趋势）
   │  │  ├─ HRV 数据（昨晚 + 7天平均 + 3天趋势）
   │  │  ├─ 身体电量（入睡前/醒来后/充电量）
   │  │  ├─ 睡眠期指标（SpO2/呼吸频率/压力/静息心率）
   │  │  └─ 近期活动（过去3天）
   │  ├─ 格式化提示词（format_morning_report_prompt）
   │  └─ 调用 LLM（ZhipuProvider, glm-4.7, max_tokens=8192）
   │
   ├─ 保存到数据库
   │  └─ db.add() → db.commit()
   │
   └─ 发送邮件通知
```

---

## 📊 数据字段规范

### HealthMetric 表字段

| 字段 | 类型 | 说明 | 错误字段名 |
|------|------|------|-----------|
| `date` | DATE | 日期（UTC） | ❌ `metric_date`（错误） |
| `sleep_hours` | FLOAT | 总睡眠时长 | ❌ `sleep_duration`（错误） |
| `deep_sleep_hours` | FLOAT | 深睡时长 | - |
| `light_sleep_hours` | FLOAT | 浅睡时长 | - |
| `rem_sleep_hours` | FLOAT | REM 睡眠时长 | - |
| `resting_heart_rate` | INTEGER | 静息心率（BPM） | - |
| `stress_level` | INTEGER | 压力水平（0-100） | - |
| `body_battery` | INTEGER | 身体电量（0-100） | - |
| `body_battery_before_sleep` | INTEGER | 入睡前身体电量 | - |
| `hrv_last_night` | INTEGER | 昨晚 HRV（ms） | - |
| `steps` | INTEGER | 步数 | - |
| `calories` | INTEGER | 卡路里消耗 | - |
| `exercise_minutes` | INTEGER | 运动时长（分钟） | - |

**重要**：所有 HealthMetric 查询必须使用正确的字段名：
- ✅ `HealthMetric.date`
- ❌ `HealthMetric.metric_date`（错误）

---

## 🔐 OAuth Token 管理流程

### Token 存储位置

- **数据库**：`garmin_connections` 表
- **字段**：`garmin_oauth_tokens`（TEXT，加密存储）
- **加密方式**：Fernet 对称加密（`encrypt_token` / `decrypt_token`）

### Token 生命周期

```
首次登录（用户名/密码）
  ↓
Garmin 服务器验证
  ↓
返回 OAuth tokens（OAuth1 + OAuth2）
  ↓
序列化 tokens
  ↓
加密存储到 garmin_oauth_tokens
  ↓
sync_status = "connected"

后续同步
  ↓
读取并解密 tokens
  ↓
反序列化到 client
  ↓
验证 tokens（client.connectapi）
  ├─ 成功 → 直接使用，无需登录
  └─ 失败 → 重新登录 → 更新 tokens
```

### 关键逻辑

```python
# 1. 优先使用 OAuth tokens
if connection.garmin_oauth_tokens:
    token_str = decrypt_token(connection.garmin_oauth_tokens)
    if deserialize_oauth_tokens(token_str, client):
        profile = client.connectapi("/userprofile-service/socialProfile")
        if profile:
            connection.sync_status = "connected"
            connection.last_error = None
            db.commit()

# 2. Tokens 失败才重新登录
if not tokens_used:
    client, user_info = login(username, password, is_cn)
    new_oauth_tokens = serialize_oauth_tokens(client)
    connection.garmin_oauth_tokens = encrypt_token(new_oauth_tokens)
    connection.sync_status = "connected"
    db.commit()
```

---

## 🛠️ Cron 任务配置

### 定时任务设置

- **早报任务**：每天 09:00
- **晚报任务**：每天 21:00
- **执行方式**：APScheduler AsyncIOScheduler

### 早报检查睡眠数据

```python
yesterday = date.today() - timedelta(days=1)
sleep_data = db.query(HealthMetric).filter(
    HealthMetric.user_id == user_id,
    HealthMetric.date == yesterday,  # ✅ 正确字段名
    HealthMetric.sleep_hours.isnot(None)  # ✅ 正确字段名
).first()
```

### 晚报不检查睡眠数据

晚报任务**不需要**检查睡眠数据，直接生成即可。

---

## 📝 报告生成流程总结

### 修改历史

**2026-03-24**：
- ✅ PR #8：晚报 Cron 任务优化
  - 同步失败时中断处理
  - 晚报已存在时删除并重新生成
- ✅ PR #9：OAuth token 逻辑优化
  - 移除 sync_status 前置检查
  - 优先使用 OAuth tokens
  - tokens 有效后更新 sync_status = "connected"
- ✅ Commit ec935bb：修复字段名错误
  - `metric_date` → `date`
  - `sleep_duration` → `sleep_hours`

### 验证流程

1. **手动同步测试**
   - 直接调用 `garmin_service.refresh_garmin_data()`
   - 不需要启动 FastAPI 服务器

2. **删除并重新生成**
   - 删除已存在的晚报
   - 调用 `generate_evening_report()`
   - 验证新报告生成成功

3. **提示词检查**
   - 查看生成的 `input_context`
   - 确保包含完整数据
   - 验证 LLM 模型调用成功

### 报告生成时间

- **步骤 1-4**（同步数据）：1-3 秒
- **步骤 5-6**（生成报告）：2-5 秒
- **总计**：3-8 秒

---

## 🎯 关键经验

### OAuth Token 优化要点

1. **移除 sync_status 前置检查**
   - 旧逻辑：`if sync_status != "connected": raise`
   - 新逻辑：不管状态，直接尝试用 tokens
   - tokens 失败才标记 error

2. **更新 sync_status**
   - tokens 验证成功 → `sync_status = "connected"`
   - 重新登录成功 → `sync_status = "connected"`
   - 认证失败 → `sync_status = "error"`

3. **避免重复登录**
   - OAuth tokens 有效时无需重新登录
   - 登录一次，后续自动复用

### Cron 任务优化要点

1. **晚报任务**
   - 同步失败 → 中断，不继续
   - 已存在晚报 → 删除并重新生成

2. **早报任务**
   - 检查睡眠数据 → 不存在则中断，发送 QQ 提醒
   - 已存在早报 → 跳过（不删除）

3. **字段名一致性**
   - 所有查询必须使用 `HealthMetric.date` 和 `HealthMetric.sleep_hours`
   - 避免使用错误字段名 `metric_date` 和 `sleep_duration`

---

## 💾 测试文件清理

所有测试脚本执行完毕后需要删除：
- `test_step*.py`
- `check_*.py`
- `update_*.py`
- `run_*.py`
- `backup_*.json`

**清理命令**：
```bash
rm backend/test_*.py backend/check_*.py backend/update_*.py backend/run_*.py backend/backup_*.json
```

---

## 🔗 相关文件路径

### 核心文件
- `backend/app/tasks/scheduler.py` - Cron 任务调度
- `backend/app/services/garmin.py` - Garmin 数据同步
- `backend/app/services/report_generator.py` - 报告生成
- `backend/app/services/report_data_aggregator.py` - 数据聚合
- `backend/app/api/v1/reports.py` - 报告 API
- `backend/app/api/v1/garmin.py` - Garmin API

### 配置文件
- `backend/.env` - 环境变量
- `backend/app/core/config.py` - 配置加载

### 数据库模型
- `backend/app/models/__init__.py` - 所有模型定义

---

## 📌 重要提醒

1. **字段名错误会导致 Cron 任务失败**
   - `metric_date` → `date`
   - `sleep_duration` → `sleep_hours`
   - 错误会导致 `Garmin sync failed` 异常

2. **OAuth Token 验证失败会导致重新登录**
   - 如果 tokens 无效，会重新登录
   - 登录成功后更新 tokens
   - 记录到日志便于排查

3. **同步失败会中断处理**
   - 晚报任务：同步失败 → 跳过该用户
   - 早报任务：同步失败 → 跳过该用户

4. **不要直接在主仓库修改代码**
   - 必须使用 git worktree
   - 通过 PR 提交修改
   - 遵循项目规范

---

_最后更新：2026-03-25 00:03_