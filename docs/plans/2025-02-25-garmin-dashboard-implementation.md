# Garmin Dashboard 重设计实现计划

## 设计文档

参考: `docs/plans/2025-02-25-garmin-dashboard-redesign.md`

## 实现阶段

### 阶段一：后端清理

#### 任务 1.1: 删除 Strava 相关文件
- [ ] 删除 `backend/app/services/strava.py`
- [ ] 删除 `backend/app/api/v1/strava.py`

#### 任务 1.2: 清理数据库模型
文件: `backend/app/models/__init__.py`
- [ ] 删除 `WorkMetric` 类 (约第 110-132 行)
- [ ] 删除 `StravaConnection` 类 (约第 172-209 行)
- [ ] 删除 `ActivityMetric` 类 (约第 249-283 行)
- [ ] 删除 User 模型中的相关 relationship
- [ ] 删除 UserPreference 中的 `show_work_time` 和 `show_focus` 字段

#### 任务 1.3: 清理 Pydantic Schemas
文件: `backend/app/schemas/__init__.py`
- [ ] 删除 `WorkMetric*` schemas
- [ ] 删除 `Strava*` schemas
- [ ] 删除 DailyTrendData 中的 work 字段
- [ ] 删除 OverviewMetric 中的 work 字段
- [ ] 删除 SummaryMetric 中的 `work_hours` 字段
- [ ] 删除 UserPreferenceBase 中的 work 相关字段

#### 任务 1.4: 清理 API 端点
文件: `backend/app/api/v1/ingest.py`
- [ ] 删除 `ingest_work_data` 端点
- [ ] 删除相关导入

#### 任务 1.5: 清理 Dashboard 服务
文件: `backend/app/services/dashboard.py`
- [ ] 删除所有 WorkMetric 查询和聚合
- [ ] 删除 work_hours 相关计算

#### 任务 1.6: 清理配置
文件: `backend/app/core/config.py`
- [ ] 删除 Strava OAuth 配置字段

#### 任务 1.7: 清理路由注册
文件: `backend/main.py`
- [ ] 删除 Strava 路由注册

### 阶段二：前端清理

#### 任务 2.1: 删除 Strava 相关文件
- [ ] 删除 `frontend/components/strava-connection-card.tsx`
- [ ] 删除 `frontend/components/strava-activities-panel.tsx`
- [ ] 删除 `frontend/app/settings/strava/page.tsx`

#### 任务 2.2: 清理类型定义
文件: `frontend/types/api.ts`
- [ ] 删除 WorkMetric 相关类型
- [ ] 删除 Strava 相关类型

#### 任务 2.3: 清理 API 客户端
文件: `frontend/lib/api.ts`
- [ ] 删除 WorkMetric API 函数
- [ ] 删除 Strava API 函数

#### 任务 2.4: 清理设置页面
文件: `frontend/app/settings/page.tsx`
- [ ] 删除 Strava 设置链接

#### 任务 2.5: 清理导航
文件: `frontend/components/site-header.tsx`
- [ ] 删除 Strava 导航项

#### 任务 2.6: 删除工作卡片组件
- [ ] 删除 `frontend/components/dashboard/work-card.tsx` (如果存在)
- [ ] 从 Dashboard 页面移除工作卡片引用

### 阶段三：验证

#### 任务 3.1: 后端验证
- [ ] 运行后端服务，确认启动无错误
- [ ] 测试 Garmin 相关 API 端点
- [ ] 测试 Dashboard API 端点

#### 任务 3.2: 前端验证
- [ ] 运行前端服务，确认编译无错误
- [ ] 测试 Dashboard 页面加载
- [ ] 测试 Garmin 连接功能

## 执行顺序

1. 先执行后端清理（阶段一）
2. 再执行前端清理（阶段二）
3. 最后验证（阶段三）

## 风险点

- 数据库中已有的 WorkMetric 和 Strava 数据会丢失
- 需要确保所有引用都被清理干净，避免运行时错误
