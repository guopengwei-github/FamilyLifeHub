# 佳明早晚健康报告模块设计文档

> 创建日期: 2026-03-01

## 1. 项目概述

在 FamilyLifeHub 项目中新增自动化健康分析模块，每天定时（早晨和晚间）抓取用户的 Garmin 生理监测数据，结合历史趋势，通过 LLM 生成个性化的精力管理报告。

## 2. 核心需求

### 2.1 晨间启动报告 (Morning Readiness Report)
- **触发时间**: 每天 09:00
- **数据输入**: 睡眠数据、HRV 数据、今晨身体电量、静息心率 + 过去3-7天趋势
- **输出内容**:
  1. 系统恢复评估
  2. 今日安排建议（工作、午睡、脑力活动）
  3. 今日运动处方

### 2.2 晚间复盘报告 (Evening Review Report)
- **触发时间**: 每天 22:00
- **数据输入**: 全天心率、压力分布、身体电量消耗、活动数据 + 过去3-7天趋势
- **输出内容**:
  1. 今日消耗总结
  2. 高压精准归因
  3. 明日优化建议
  4. 今晚入睡干预

## 3. 技术方案

### 3.1 架构设计

采用单体服务架构，与现有项目保持一致：

```
FastAPI Backend
├── APScheduler (定时任务)
│   ├── 09:00 晨间报告生成
│   └── 22:00 晚间报告生成
├── app/services/llm/
│   ├── base.py        # LLM 抽象接口
│   ├── zhipu.py       # 智谱 GLM 实现
│   └── prompts.py     # Prompt 模板
├── app/services/
│   ├── report_generator.py
│   └── report_data_aggregator.py
└── app/tasks/
    ├── scheduler.py
    └── retry.py
```

### 3.2 数据模型

#### User 模型扩展

```python
class User(Base):
    # ... 现有字段 ...

    # 用户画像
    age = Column(Integer, nullable=True)           # 年龄
    gender = Column(String(10), nullable=True)     # 性别: 'male', 'female', 'other'
    weight_kg = Column(Float, nullable=True)       # 体重(kg)
```

#### HealthReport 新表

```python
class HealthReport(Base):
    __tablename__ = "health_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    report_date = Column(Date, nullable=False, index=True)
    report_type = Column(String(20), nullable=False)  # 'morning' 或 'evening'

    input_context = Column(Text, nullable=True)   # LLM 输入（调试用）
    content = Column(Text, nullable=False)        # 报告内容（Markdown）

    generated_at = Column(DateTime, default=datetime.now(timezone.utc))
    llm_model = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('user_id', 'report_date', 'report_type', name='uq_user_date_type'),
    )
```

### 3.3 LLM 服务接口

```python
# app/services/llm/base.py
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = None, max_tokens: int = 2000) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

# app/services/llm/zhipu.py
class ZhipuProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "glm-4-flash"):
        self.client = ZhipuAI(api_key=api_key)
        self._model = model
```

### 3.4 Prompt 设计

数据注入策略：

| 数据类型 | 晨间报告 | 晚间报告 |
|---------|---------|---------|
| 睡眠数据 | 昨晚 + 过去7天趋势 | - |
| HRV | 昨夜值 + 7天均值 + 3天趋势 | - |
| 身体电量 | 今晨起始值 | 全天消耗 + 过去3天对比 |
| 压力 | - | 今日分布 + 7天均值对比 |
| 心率 | - | 今日 + 7天均值对比 |
| 活动 | 过去3天运动情况 | 今日 + 7天均值对比 |

详见 `app/services/llm/prompts.py`

### 3.5 定时任务

```python
# app/tasks/scheduler.py

# 晨间报告：每天 09:00
scheduler.add_job(
    generate_morning_reports_job,
    trigger=CronTrigger(hour=9, minute=0),
    id='morning_report',
    misfire_grace_time=3600
)

# 晚间报告：每天 22:00
scheduler.add_job(
    generate_evening_reports_job,
    trigger=CronTrigger(hour=22, minute=0),
    id='evening_report',
    misfire_grace_time=3600
)
```

### 3.6 失败处理

- 静默失败，不影响其他用户
- 最多重试 3 次
- 重试间隔：1小时、4小时、12小时

### 3.7 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/reports/morning` | GET | 获取晨间报告 |
| `/api/v1/reports/evening` | GET | 获取晚间报告 |
| `/api/v1/reports/history` | GET | 获取历史报告列表 |
| `/api/v1/reports/regenerate` | POST | 手动重新生成报告 |
| `/api/v1/users/me/profile` | PATCH | 更新用户画像 |

### 3.8 前端集成

在 Dashboard 页面顶部新增两个报告卡片：

```
┌─────────────────────────────────────────────────────────┐
│  ┌─────────────────────┐  ┌─────────────────────┐       │
│  │   晨间报告卡片       │  │   晚间报告卡片       │       │
│  │   (09:00后显示)      │  │   (22:00后显示)      │       │
│  └─────────────────────┘  └─────────────────────┘       │
├─────────────────────────────────────────────────────────┤
│  现有的 Overview Panel                                   │
├─────────────────────────────────────────────────────────┤
│  现有的 Trend Charts                                     │
└─────────────────────────────────────────────────────────┘
```

## 4. 依赖项

### 4.1 后端新增依赖

```txt
zhipuai>=2.0.0
apscheduler>=3.10.0
```

### 4.2 环境变量

```bash
ZHIPU_API_KEY=your_zhipu_api_key_here
ZHIPU_MODEL=glm-4-flash
REPORT_RETRY_MAX=3
REPORT_RETRY_INTERVALS=1,4,12
```

## 5. 文件结构

```
backend/
├── app/
│   ├── api/v1/
│   │   ├── reports.py          # 新增
│   │   └── users.py            # 修改
│   ├── models/__init__.py      # 修改
│   ├── schemas/__init__.py     # 修改
│   ├── services/
│   │   ├── llm/                # 新增目录
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── zhipu.py
│   │   │   └── prompts.py
│   │   ├── report_generator.py # 新增
│   │   └── report_data_aggregator.py  # 新增
│   └── tasks/                  # 新增目录
│       ├── __init__.py
│       ├── scheduler.py
│       └── retry.py
├── requirements.txt            # 修改
└── .env                        # 修改

frontend/
├── components/
│   ├── reports/                # 新增目录
│   │   ├── report-card.tsx
│   │   ├── morning-report.tsx
│   │   ├── evening-report.tsx
│   │   └── report-history.tsx
│   └── settings/
│       └── profile-form.tsx    # 新增
├── app/page.tsx                # 修改
├── lib/api.ts                  # 修改
└── types/api.ts                # 修改
```

## 6. 扩展性设计

- LLM 提供商通过抽象接口隔离，后续可轻松添加其他提供商
- Prompt 模板独立文件，方便调整
- 数据聚合服务独立，可复用
