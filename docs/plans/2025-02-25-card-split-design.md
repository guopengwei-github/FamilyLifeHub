# 卡片拆分设计方案

## 背景

当前 Dashboard 的「运动&健康」卡片（ActivityHealthCard）使用 Tab 切换两个视图。
本方案将其拆分为两个独立卡片，并充分利用 GarminActivity 的详细活动数据。

## 设计目标

1. 将 ActivityHealthCard 拆分为：运动卡片 + 身体状态卡片
2. 以趋势分析为主，支持周/月视图切换
3. 展示具体活动详情（跑步、骑行等）

## 最终卡片结构

拆分后 Dashboard 共有 4 个卡片：

| 卡片 | 组件名 | 主要内容 |
|------|--------|----------|
| 睡眠分析 | SleepCard | 睡眠评分、时长、阶段分布 |
| 运动 | ActivityCard | 步数/卡路里/距离 + 活动列表 + 趋势 |
| 身体状态 | BodyStatusCard | 身体电量、血氧、呼吸、心率 + 恢复建议 |
| 压力水平 | StressCard | 压力值、状态、趋势 |

---

## 卡片 1：运动卡片 (ActivityCard)

### 布局设计

```
┌─────────────────────────────────────────┐
│  🏃 运动                    [周/月切换]  │
├─────────────────────────────────────────┤
│  今日汇总                                │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐       │
│  │步数  │ │卡路里│ │距离  │ │时长  │       │
│  │8,432│ │ 420 │ │5.2km│ │45min│       │
│  └─────┘ └─────┘ └─────┘ └─────┘       │
├─────────────────────────────────────────┤
│  最近活动                                │
│  ┌─────────────────────────────────────┐│
│  │ 🏃 晨跑  今天 07:30                  ││
│  │ 5.2km · 32min · 心率142 · 配速6'10" ││
│  └─────────────────────────────────────┘│
│  ┌─────────────────────────────────────┐│
│  │ 🚴 骑行  昨天 18:00                  ││
│  │ 15km · 45min · 心率128 · 20km/h    ││
│  └─────────────────────────────────────┘│
├─────────────────────────────────────────┤
│  周趋势图（步数/卡路里折线图）            │
│  ▁▃▅▇▅▃▁                               │
└─────────────────────────────────────────┘
```

### 数据来源

| 区域 | 数据源 | 字段 |
|------|--------|------|
| 今日汇总 | HealthMetric | steps, calories, distance_km, exercise_minutes |
| 最近活动 | GarminActivity | activity_type, distance_meters, duration_seconds, average_heartrate, avg_speed_mps |
| 趋势图 | HealthMetric (7/30天) | steps, calories 聚合 |

### 活动类型图标映射

| activity_type | 图标 | 显示名称 |
|---------------|------|----------|
| running | 🏃 | 跑步 |
| cycling | 🚴 | 骑行 |
| swimming | 🏊 | 游泳 |
| walking | 🚶 | 步行 |
| strength | 💪 | 力量训练 |
| other | 🏋️ | 其他 |

---

## 卡片 2：身体状态卡片 (BodyStatusCard)

### 布局设计

```
┌─────────────────────────────────────────┐
│  💪 身体状态                [周/月切换]  │
├─────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────┐ │
│  │   身体电量    │  │  恢复状态        │ │
│  │     🔋       │  │  ✅ 恢复良好     │ │
│  │     72%      │  │  建议：适合运动   │ │
│  │  ████████░░  │  │                  │ │
│  └──────────────┘  └──────────────────┘ │
├─────────────────────────────────────────┤
│  生理指标                                │
│  ┌─────┐ ┌─────┐ ┌─────┐               │
│  │血氧  │ │呼吸  │ │心率  │               │
│  │ 98% │ │15次  │ │58bpm│               │
│  │ ↑2% │ │ →   │ │ ↓3  │               │
│  └─────┘ └─────┘ └─────┘               │
├─────────────────────────────────────────┤
│  7日趋势（身体电量折线图）                │
│  ▃▅▇▅▃▅▇                               │
└─────────────────────────────────────────┘
```

### 数据来源

| 区域 | 数据源 | 字段 |
|------|--------|------|
| 身体电量 | HealthMetric | body_battery |
| 生理指标 | HealthMetric | spo2, respiration_rate, resting_hr |
| 趋势图 | HealthMetric (7/30天) | body_battery 聚合 |

### 恢复状态计算逻辑

```python
def get_recovery_status(body_battery: int, stress_level: int) -> tuple[str, str]:
    """返回 (状态, 建议)"""
    if body_battery >= 70 and stress_level <= 30:
        return ("✅ 恢复良好", "适合高强度运动")
    elif body_battery >= 50 and stress_level <= 50:
        return ("🟡 恢复中", "适合中等强度运动")
    elif body_battery >= 30:
        return ("🟠 需要休息", "建议轻度活动或休息")
    else:
        return ("🔴 疲劳", "建议充分休息")
```

---

## 实现计划

### Phase 1: 创建新组件

1. 创建 `ActivityCard` 组件
2. 创建 `BodyStatusCard` 组件
3. 添加活动列表子组件 `RecentActivities`

### Phase 2: API 扩展

1. 添加 `/api/v1/activities/recent` 端点
2. 扩展 dashboard 服务支持活动数据

### Phase 3: 集成与清理

1. 在 Dashboard 页面集成新卡片
2. 删除旧的 `ActivityHealthCard` 组件
3. 更新 CARD_IDS 常量

---

## 文件变更清单

### 新增文件

- `frontend/components/dashboard/activity-card.tsx`
- `frontend/components/dashboard/body-status-card.tsx`
- `frontend/components/dashboard/recent-activities.tsx`

### 修改文件

- `frontend/app/page.tsx` - 替换卡片引用
- `frontend/types/api.ts` - 更新 CARD_IDS
- `backend/app/api/v1/dashboard.py` - 添加活动端点

### 删除文件

- `frontend/components/dashboard/activity-health-card.tsx`
