# 首页仪表盘重设计实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重新设计首页仪表盘，采用卡片式布局，支持佳明数据和手动输入数据混合展示，每个卡片可独立控制显示/隐藏。

**Architecture:**
1. 后端扩展 HealthMetric 模型增加新字段（步数、卡路里、身体电量等）
2. 后端新增 UserPreference.hidden_cards 字段用于持久化卡片显示状态
3. 后端新增 summary API 端点返回核心数据快照
4. 前端创建新的 dashboard 组件目录，重构页面为模块化卡片组件
5. 前端实现卡片可见性控制逻辑和成员切换功能

**Tech Stack:**
- 后端: FastAPI, SQLAlchemy, SQLite, Pydantic
- 前端: Next.js 14, TypeScript, Tailwind CSS, Lucide React, Framer Motion

---

## Task 1: 扩展后端数据模型

**Files:**
- Modify: `backend/app/models/__init__.py:66-93` (HealthMetric class)
- Modify: `backend/app/models/__init__.py:37-63` (UserPreference class)

**Step 1: 扩展 HealthMetric 模型**

在 `backend/app/models/__init__.py` 的 `HealthMetric` 类中添加新字段。找到第 84 行 `exercise_minutes` 字段之后，添加以下内容：

```python
# Garmin advanced metrics (新增)
steps = Column(Integer, nullable=True)           # 步数
calories = Column(Integer, nullable=True)        # 卡路里消耗
distance_km = Column(Float, nullable=True)       # 距离(公里)
body_battery = Column(Integer, nullable=True)    # 身体电量 (0-100)
spo2 = Column(Float, nullable=True)              # 血氧饱和度 (%)
respiration_rate = Column(Float, nullable=True)  # 呼吸频率 (次/分)
resting_hr = Column(Integer, nullable=True)      # 静息心率 (BPM)
sleep_score = Column(Integer, nullable=True)     # 睡眠质量评分 (0-100)
```

**Step 2: 扩展 UserPreference 模型**

在 `backend/app/models/__init__.py` 的 `UserPreference` 类中，找到第 53 行 `show_sleep_stages` 字段之后，添加：

```python
# Card visibility settings (新增)
hidden_cards = Column(Text, nullable=True)       # JSON string: 隐藏的卡片ID列表
default_view_tab = Column(String(50), default='activity', nullable=False)  # 默认Tab: activity/health
```

**Step 3: 验证模型变更**

运行后端服务，确保数据库迁移成功（SQLite 会自动创建新列）：

```bash
cd backend
python main.py
```

预期输出：服务正常启动，无数据库错误。检查新列是否已创建：

```bash
sqlite3 family_life_hub.db ".schema health_metrics"
```

预期输出：包含新增的 steps, calories, distance_km 等字段。

**Step 4: 提交**

```bash
cd backend
git add app/models/__init__.py
git commit -m "feat: extend HealthMetric and UserPreference models for dashboard redesign

- Add steps, calories, distance_km, body_battery, spo2, respiration_rate, resting_hr, sleep_score to HealthMetric
- Add hidden_cards and default_view_tab to UserPreference"
```

---

## Task 2: 更新 Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas/__init__.py`

**Step 1: 扩展 HealthMetricBase schema**

在 `backend/app/schemas/__init__.py` 的 `HealthMetricBase` 类（第 67 行）中，在 `exercise_minutes` 字段后添加：

```python
    steps: Optional[int] = Field(None, ge=0, description="Daily steps")
    calories: Optional[int] = Field(None, ge=0, description="Calories burned")
    distance_km: Optional[float] = Field(None, ge=0, description="Distance in kilometers")
    body_battery: Optional[int] = Field(None, ge=0, le=100, description="Body battery (0-100)")
    spo2: Optional[float] = Field(None, ge=0, le=100, description="Blood oxygen saturation (%)")
    respiration_rate: Optional[float] = Field(None, ge=0, le=100, description="Respiration rate (breaths/min)")
    resting_hr: Optional[int] = Field(None, ge=30, le=200, description="Resting heart rate (BPM)")
    sleep_score: Optional[int] = Field(None, ge=0, le=100, description="Sleep quality score (0-100)")
```

**Step 2: 扩展 UserPreferenceBase schema**

在 `backend/app/schemas/__init__.py` 的 `UserPreferenceBase` 类（第 294 行）中，在 `show_sleep_stages` 字段后添加：

```python
    hidden_cards: Optional[str] = Field(None, description="JSON string of hidden card IDs")
    default_view_tab: str = Field('activity', description="Default view tab: activity or health")
```

**Step 3: 新增 SummaryResponse schema**

在 `backend/app/schemas/__init__.py` 文件末尾（第 323 行之后）添加：

```python
# ============ Dashboard Summary Schemas (新增) ============

class SummaryMetric(BaseModel):
    """Core summary metric for dashboard header."""
    sleep_hours: Optional[float] = None
    steps: Optional[int] = None
    calories: Optional[int] = None
    work_hours: Optional[float] = None
    stress_level: Optional[int] = None


class SummaryResponse(BaseModel):
    """Response schema for dashboard summary endpoint."""
    date: date_type
    user_id: int
    user_name: str
    avatar: Optional[str] = None
    metrics: SummaryMetric
```

**Step 4: 提交**

```bash
cd backend
git add app/schemas/__init__.py
git commit -m "feat: update schemas for extended health metrics and dashboard summary"
```

---

## Task 3: 新增 Dashboard Summary API 端点

**Files:**
- Modify: `backend/app/api/v1/dashboard.py`
- Modify: `backend/app/services/dashboard.py`

**Step 1: 在 service 层添加 summary 聚合逻辑**

在 `backend/app/services/dashboard.py` 中添加新函数：

```python
from app.schemas import SummaryResponse, SummaryMetric
from app.models import User
from sqlalchemy.orm import Session
from datetime import date


def get_user_summary(db: Session, user_id: int, target_date: date = None) -> dict:
    """
    Get user's core summary metrics for dashboard header.
    """
    if target_date is None:
        target_date = date.today()

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Get health metric for target date
    health_metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == target_date
    ).first()

    # Get work metrics aggregated for target date
    from sqlalchemy import func
    work_metrics = db.query(
        func.sum(WorkMetric.screen_time_minutes).label('total_minutes'),
        func.avg(WorkMetric.focus_score).label('avg_focus')
    ).filter(
        WorkMetric.user_id == user_id,
        func.date(WorkMetric.timestamp) == target_date
    ).first()

    summary = {
        'date': target_date,
        'user_id': user.id,
        'user_name': user.name,
        'avatar': user.avatar,
        'metrics': {
            'sleep_hours': health_metric.sleep_hours if health_metric else None,
            'steps': getattr(health_metric, 'steps', None) if health_metric else None,
            'calories': getattr(health_metric, 'calories', None) if health_metric else None,
            'work_hours': round(work_metrics.total_minutes / 60, 1) if work_metrics.total_minutes else None,
            'stress_level': health_metric.stress_level if health_metric else None,
        }
    }

    return summary
```

**Step 2: 在 dashboard router 添加 summary 端点**

在 `backend/app/api/v1/dashboard.py` 中添加新路由：

```python
@router.get("/summary", response_model=SummaryResponse)
async def get_dashboard_summary(
    target_date: Optional[date_type] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's summary metrics for dashboard header.
    """
    from app.services.dashboard import get_user_summary

    summary = get_user_summary(db, current_user.id, target_date)
    return summary
```

**Step 3: 测试端点**

```bash
# 启动后端
cd backend
python main.py

# 在另一个终端测试
curl http://localhost:8000/api/v1/dashboard/summary -H "Authorization: Bearer YOUR_TOKEN"
```

预期输出：包含 date, user_id, user_name, metrics 的 JSON 响应。

**Step 4: 提交**

```bash
cd backend
git add app/api/v1/dashboard.py app/services/dashboard.py
git commit -m "feat: add /summary endpoint for dashboard header metrics"
```

---

## Task 4: 新增卡片可见性 API 端点

**Files:**
- Modify: `backend/app/api/v1/preferences.py`

**Step 1: 添加更新 hidden_cards 端点**

在 `backend/app/api/v1/preferences.py` 中添加新路由：

```python
class HiddenCardsUpdate(BaseModel):
    """Schema for updating hidden cards."""
    hidden_cards: Optional[str] = Field(None, description="JSON string of hidden card IDs")


@router.put("/hidden-cards")
async def update_hidden_cards(
    data: HiddenCardsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the list of hidden dashboard cards.
    """
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()

    if preference:
        preference.hidden_cards = data.hidden_cards
        preference.updated_at = datetime.utcnow()
    else:
        # Create if not exists
        preference = UserPreference(
            user_id=current_user.id,
            hidden_cards=data.hidden_cards
        )
        db.add(preference)

    db.commit()
    db.refresh(preference)

    return {"message": "Hidden cards updated", "hidden_cards": preference.hidden_cards}
```

**Step 2: 测试端点**

```bash
curl -X PUT http://localhost:8000/api/v1/preferences/hidden-cards \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"hidden_cards": "[\"sleep\",\"work\"]"}'
```

预期输出：`{"message": "Hidden cards updated", "hidden_cards": "[\"sleep\",\"work\"]"}`

**Step 3: 提交**

```bash
cd backend
git add app/api/v1/preferences.py
git commit -m "feat: add /preferences/hidden-cards endpoint"
```

---

## Task 5: 更新前端类型定义

**Files:**
- Modify: `frontend/types/api.ts`

**Step 1: 扩展 HealthMetric 类型**

在 `frontend/types/api.ts` 的 `HealthMetric` 接口（第 35 行）中，在 `exercise_minutes` 后添加：

```typescript
  // Garmin advanced metrics
  steps?: number | null;
  calories?: number | null;
  distance_km?: number | null;
  body_battery?: number | null;
  spo2?: number | null;
  respiration_rate?: number | null;
  resting_hr?: number | null;
  sleep_score?: number | null;
```

**Step 2: 扩展 HealthMetricForm 类型**

在 `frontend/types/api.ts` 的 `HealthMetricForm` 接口（第 50 行）中，添加相同字段：

```typescript
  steps?: number;
  calories?: number;
  distance_km?: number;
  body_battery?: number;
  spo2?: number;
  respiration_rate?: number;
  resting_hr?: number;
  sleep_score?: number;
```

**Step 3: 扩展 UserPreference 类型**

在 `frontend/types/api.ts` 的 `UserPreference` 接口（第 213 行）中，添加：

```typescript
  hidden_cards?: string | null;
  default_view_tab?: string;
```

**Step 4: 扩展 UserPreferenceUpdate 类型**

在 `frontend/types/api.ts` 的 `UserPreferenceUpdate` 接口（第 226 行）中，添加：

```typescript
  hidden_cards?: string;
  default_view_tab?: string;
```

**Step 5: 新增 SummaryResponse 类型**

在 `frontend/types/api.ts` 文件末尾添加：

```typescript
// ============ Dashboard Summary Types ============

export interface SummaryMetric {
  sleep_hours: number | null;
  steps: number | null;
  calories: number | null;
  work_hours: number | null;
  stress_level: number | null;
}

export interface SummaryResponse {
  date: string;
  user_id: number;
  user_name: string;
  avatar: string | null;
  metrics: SummaryMetric;
}

// ============ Card IDs ============

export const CARD_IDS = {
  SLEEP: 'sleep',
  ACTIVITY_HEALTH: 'activity_health',
  WORK: 'work',
  STRESS: 'stress',
  TRENDS: 'trends'
} as const;

export type CardId = typeof CARD_IDS[keyof typeof CARD_IDS];
```

**Step 6: 提交**

```bash
cd frontend
git add types/api.ts
git commit -m "feat: extend TypeScript types for dashboard redesign"
```

---

## Task 6: 更新前端 API 客户端

**Files:**
- Modify: `frontend/lib/api.ts`

**Step 1: 导入新类型**

在 `frontend/lib/api.ts` 顶部的 import 语句中添加：

```typescript
type SummaryResponse,
} from '@/types/api';
```

修改为：

```typescript
type SummaryResponse,
type CardId,
CARD_IDS,
} from '@/types/api';
```

**Step 2: 添加 summary API 函数**

在 `frontend/lib/api.ts` 的 Dashboard Endpoints 部分（第 270 行之后）添加：

```typescript
/**
 * Get dashboard summary for current user
 */
export async function getDashboardSummary(targetDate?: string): Promise<SummaryResponse> {
  const params = targetDate ? `?target_date=${targetDate}` : '';
  return fetchAPI<SummaryResponse>(`/api/v1/dashboard/summary${params}`);
}
```

**Step 3: 添加 hidden cards API 函数**

在 `frontend/lib/api.ts` 的 Preferences Endpoints 部分（第 433 行之后）添加：

```typescript
/**
 * Update hidden cards preference
 */
export async function updateHiddenCards(hiddenCards: string): Promise<{ message: string; hidden_cards: string | null }> {
  return fetchAPI('/api/v1/preferences/hidden-cards', {
    method: 'PUT',
    body: JSON.stringify({ hidden_cards: hiddenCards }),
  });
}
```

**Step 4: 提交**

```bash
cd frontend
git add lib/api.ts
git commit -m "feat: add API client functions for summary and hidden cards"
```

---

## Task 7: 创建前端 Dashboard 组件目录结构

**Files:**
- Create: `frontend/components/dashboard/`
- Create: `frontend/components/dashboard/card-visibility-control.tsx`
- Create: `frontend/components/dashboard/user-summary-card.tsx`

**Step 1: 创建目录**

```bash
mkdir -p frontend/components/dashboard
```

**Step 2: 创建卡片可见性控制组件**

创建 `frontend/components/dashboard/card-visibility-control.tsx`:

```typescript
'use client';

import { Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';

interface CardVisibilityControlProps {
  cardId: string;
  isHidden: boolean;
  onToggle: (cardId: string, hidden: boolean) => void;
  className?: string;
}

export function CardVisibilityControl({
  cardId,
  isHidden,
  onToggle,
  className = ''
}: CardVisibilityControlProps) {
  const [isAnimating, setIsAnimating] = useState(false);

  const handleToggle = () => {
    setIsAnimating(true);
    onToggle(cardId, !isHidden);
    setTimeout(() => setIsAnimating(false), 300);
  };

  return (
    <button
      onClick={handleToggle}
      className={`p-2 rounded-md hover:bg-muted transition-colors ${className}`}
      title={isHidden ? 'Show card' : 'Hide card'}
      aria-label={isHidden ? 'Show card' : 'Hide card'}
    >
      {isHidden ? (
        <EyeOff className="h-4 w-4 text-muted-foreground" />
      ) : (
        <Eye className="h-4 w-4" />
      )}
    </button>
  );
}
```

**Step 3: 创建用户摘要卡片组件**

创建 `frontend/components/dashboard/user-summary-card.tsx`:

```typescript
'use client';

import { Card, CardContent } from '@/components/ui/card';
import { SummaryResponse } from '@/types/api';
import { Moon, Footprints, Flame, Clock, Heart } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

interface UserSummaryCardProps {
  summary: SummaryResponse;
}

export function UserSummaryCard({ summary }: UserSummaryCardProps) {
  const { user_name, avatar, metrics } = summary;

  const summaryItems = [
    {
      icon: Moon,
      value: metrics.sleep_hours ? `${metrics.sleep_hours}h` : 'N/A',
      label: 'Sleep',
      color: 'text-blue-500',
    },
    {
      icon: Footprints,
      value: metrics.steps ? metrics.steps.toLocaleString() : 'N/A',
      label: 'Steps',
      color: 'text-green-500',
    },
    {
      icon: Flame,
      value: metrics.calories ? `${metrics.calories}` : 'N/A',
      label: 'Calories',
      color: 'text-orange-500',
    },
    {
      icon: Clock,
      value: metrics.work_hours ? `${metrics.work_hours}h` : 'N/A',
      label: 'Work',
      color: 'text-purple-500',
    },
    {
      icon: Heart,
      value: metrics.stress_level ? `${metrics.stress_level}` : 'N/A',
      label: 'Stress',
      color: 'text-red-500',
    },
  ];

  return (
    <Card className="border-2">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          {/* Left: User Info */}
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16">
              <AvatarImage src={avatar || undefined} />
              <AvatarFallback className="text-xl">
                {user_name.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div>
              <h2 className="text-2xl font-bold">{user_name}</h2>
              <p className="text-muted-foreground">
                {new Date(summary.date).toLocaleDateString('zh-CN', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  weekday: 'long'
                })}
              </p>
            </div>
          </div>

          {/* Right: Summary Metrics */}
          <div className="flex gap-8">
            {summaryItems.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label} className="text-center">
                  <Icon className={`h-6 w-6 mx-auto mb-1 ${item.color}`} />
                  <p className="text-2xl font-bold">{item.value}</p>
                  <p className="text-xs text-muted-foreground">{item.label}</p>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 4: 安装 Framer Motion**

```bash
cd frontend
npm install framer-motion
```

**Step 5: 提交**

```bash
cd frontend
git add components/dashboard/
git commit -m "feat: create dashboard component directory and base components

- Add card-visibility-control component
- Add user-summary-card component
- Install framer-motion for animations"
```

---

## Task 8: 创建运动/健康切换卡片

**Files:**
- Create: `frontend/components/dashboard/activity-health-card.tsx`
- Create: `frontend/components/ui/tabs.tsx` (if not exists)

**Step 1: 创建 tabs UI 组件（如果不存在）**

检查 `frontend/components/ui/tabs.tsx` 是否存在，如果不存在则创建：

```bash
ls frontend/components/ui/tabs.tsx 2>/dev/null || echo "需要创建 tabs 组件"
```

如果不存在，创建 shadcn tabs 组件或使用简单的实现：

```typescript
'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

interface TabsContextValue {
  value: string;
  onValueChange: (value: string) => void;
}

const TabsContext = React.createContext<TabsContextValue | undefined>(undefined);

interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

export function Tabs({ value, onValueChange, children, className }: TabsProps) {
  return (
    <TabsContext.Provider value={{ value, onValueChange }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  );
}

interface TabsListProps {
  children: React.ReactNode;
  className?: string;
}

export function TabsList({ children, className }: TabsListProps) {
  return (
    <div className={cn('inline-flex h-10 items-center justify-center rounded-md bg-muted p-1', className)}>
      {children}
    </div>
  );
}

interface TabsTriggerProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

export function TabsTrigger({ value, children, className }: TabsTriggerProps) {
  const context = React.useContext(TabsContext);
  if (!context) throw new Error('TabsTrigger must be used within Tabs');

  const isActive = context.value === value;

  return (
    <button
      onClick={() => context.onValueChange(value)}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-colors',
        isActive ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground',
        className
      )}
    >
      {children}
    </button>
  );
}

interface TabsContentProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

export function TabsContent({ value, children, className }: TabsContentProps) {
  const context = React.useContext(TabsContext);
  if (!context) throw new Error('TabsContent must be used within Tabs');

  if (context.value !== value) return null;

  return (
    <div className={cn('mt-2', className)}>
      {children}
    </div>
  );
}
```

**Step 2: 创建运动/健康切换卡片**

创建 `frontend/components/dashboard/activity-health-card.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Flame, Footprints, Clock, Route, Battery, Droplets, Lung, Heart } from 'lucide-react';
import { OverviewMetric } from '@/types/api';
import { CardVisibilityControl } from './card-visibility-control';

interface ActivityHealthCardProps {
  metric: OverviewMetric;
  onToggleVisibility: (cardId: string, hidden: boolean) => void;
}

export function ActivityHealthCard({ metric, onToggleVisibility }: ActivityHealthCardProps) {
  const [activeTab, setActiveTab] = useState('activity');

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle>运动与健康</CardTitle>
        <CardVisibilityControl
          cardId="activity_health"
          isHidden={false}
          onToggle={onToggleVisibility}
        />
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="activity">运动</TabsTrigger>
            <TabsTrigger value="health">健康</TabsTrigger>
          </TabsList>

          <TabsContent value="activity" className="space-y-4">
            <ActivityTabContent metric={metric} />
          </TabsContent>

          <TabsContent value="health" className="space-y-4">
            <HealthTabContent metric={metric} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function ActivityTabContent({ metric }: { metric: OverviewMetric }) {
  const activities = [
    {
      icon: Flame,
      value: 'calories' in metric ? (metric as any).calories : null,
      unit: 'kcal',
      label: '卡路里消耗',
      goal: 2000,
      color: 'bg-orange-500',
    },
    {
      icon: Footprints,
      value: 'steps' in metric ? (metric as any).steps : null,
      unit: '',
      label: '步数',
      goal: 10000,
      color: 'bg-green-500',
    },
    {
      icon: Clock,
      value: metric.exercise_minutes,
      unit: 'min',
      label: '活动时长',
      goal: 60,
      color: 'bg-blue-500',
    },
    {
      icon: Route,
      value: 'distance_km' in metric ? (metric as any).distance_km : null,
      unit: 'km',
      label: '距离',
      goal: 5,
      color: 'bg-purple-500',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4">
      {activities.map((item) => {
        const Icon = item.icon;
        const value = item.value ?? null;
        const percentage = value ? Math.min((value / item.goal) * 100, 100) : 0;

        return (
          <div key={item.label} className="space-y-2">
            <div className="flex items-center gap-2">
              <Icon className={`h-5 w-5 ${item.color.replace('bg-', 'text-')}`} />
              <span className="text-sm font-medium">{item.label}</span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold">
                {value !== null ? value.toLocaleString() : 'N/A'}
              </span>
              {item.unit && <span className="text-sm text-muted-foreground">{item.unit}</span>}
            </div>
            {value !== null && (
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className={`h-full ${item.color} transition-all`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              目标: {item.goal.toLocaleString()} {item.unit}
            </p>
          </div>
        );
      })}
    </div>
  );
}

function HealthTabContent({ metric }: { metric: OverviewMetric }) {
  const healthMetrics = [
    {
      icon: Battery,
      value: 'body_battery' in metric ? (metric as any).body_battery : null,
      unit: '%',
      label: '身体电量',
      getColor: (v: number) => v > 80 ? 'text-green-500' : v > 50 ? 'text-yellow-500' : 'text-red-500',
    },
    {
      icon: Droplets,
      value: 'spo2' in metric ? (metric as any).spo2 : null,
      unit: '%',
      label: '血氧饱和度',
      getColor: () => 'text-blue-500',
    },
    {
      icon: Lung,
      value: 'respiration_rate' in metric ? (metric as any).respiration_rate : null,
      unit: '/min',
      label: '呼吸频率',
      getColor: () => 'text-cyan-500',
    },
    {
      icon: Heart,
      value: 'resting_hr' in metric ? (metric as any).resting_hr : metric.resting_heart_rate,
      unit: 'bpm',
      label: '静息心率',
      getColor: () => 'text-red-500',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4">
      {healthMetrics.map((item) => {
        const Icon = item.icon;
        const value = item.value ?? null;

        return (
          <div key={item.label} className="space-y-2">
            <div className="flex items-center gap-2">
              <Icon className={`h-5 w-5 ${value !== null ? item.getColor(value) : 'text-muted-foreground'}`} />
              <span className="text-sm font-medium">{item.label}</span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className={`text-2xl font-bold ${value !== null ? item.getColor(value) : ''}`}>
                {value !== null ? value : 'N/A'}
              </span>
              {item.unit && <span className="text-sm text-muted-foreground">{item.unit}</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

**Step 3: 提交**

```bash
cd frontend
git add components/dashboard/activity-health-card.tsx components/ui/tabs.tsx
git commit -m "feat: add activity-health card with tab switching"
```

---

## Task 9: 重构睡眠卡片

**Files:**
- Create: `frontend/components/dashboard/sleep-card.tsx`

**Step 1: 创建睡眠卡片组件**

创建 `frontend/components/dashboard/sleep-card.tsx`:

```typescript
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Moon, Star } from 'lucide-react';
import { OverviewMetric } from '@/types/api';
import { CardVisibilityControl } from './card-visibility-control';

interface SleepCardProps {
  metric: OverviewMetric;
  onToggleVisibility: (cardId: string, hidden: boolean) => void;
}

function getSleepQualityInfo(score: number | null) {
  if (score === null) return { label: '无数据', color: 'text-gray-400', bgColor: 'bg-gray-400' };

  if (score >= 85) return { label: '优秀', color: 'text-green-500', bgColor: 'bg-green-500' };
  if (score >= 70) return { label: '良好', color: 'text-blue-500', bgColor: 'bg-blue-500' };
  if (score >= 50) return { label: '一般', color: 'text-yellow-500', bgColor: 'bg-yellow-500' };
  return { label: '需改善', color: 'text-red-500', bgColor: 'bg-red-500' };
}

function SleepStagesBar({ metric }: { metric: OverviewMetric }) {
  const light = metric.light_sleep_hours || 0;
  const deep = metric.deep_sleep_hours || 0;
  const rem = metric.rem_sleep_hours || 0;
  const total = light + deep + rem;

  if (total === 0) {
    return <p className="text-sm text-muted-foreground">无睡眠阶段数据</p>;
  }

  const lightPercent = (light / total) * 100;
  const deepPercent = (deep / total) * 100;
  const remPercent = (rem / total) * 100;

  return (
    <div className="space-y-2">
      <div className="h-4 rounded-full overflow-hidden flex">
        <div
          className="bg-blue-400"
          style={{ width: `${lightPercent}%` }}
          title={`浅睡: ${light.toFixed(1)}h`}
        />
        <div
          className="bg-indigo-600"
          style={{ width: `${deepPercent}%` }}
          title={`深睡: ${deep.toFixed(1)}h`}
        />
        <div
          className="bg-purple-400"
          style={{ width: `${remPercent}%` }}
          title={`REM: ${rem.toFixed(1)}h`}
        />
      </div>
      <div className="flex gap-4 text-xs">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-blue-400" />
          浅睡: {light.toFixed(1)}h
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-indigo-600" />
          深睡: {deep.toFixed(1)}h
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-purple-400" />
          REM: {rem.toFixed(1)}h
        </span>
      </div>
    </div>
  );
}

export function SleepCard({ metric, onToggleVisibility }: SleepCardProps) {
  const sleepScore = 'sleep_score' in metric ? (metric as any).sleep_score : null;
  const qualityInfo = getSleepQualityInfo(sleepScore);
  const totalSleep = metric.sleep_hours;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="flex items-center gap-2">
          <Moon className="h-5 w-5 text-blue-500" />
          睡眠分析
        </CardTitle>
        <CardVisibilityControl
          cardId="sleep"
          isHidden={false}
          onToggle={onToggleVisibility}
        />
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Total Sleep */}
        <div className="flex items-end justify-between">
          <div>
            <p className="text-sm text-muted-foreground">昨晚睡眠</p>
            <p className="text-3xl font-bold">
              {totalSleep ? `${Math.floor(totalSleep)}小时${Math.round((totalSleep % 1) * 60)}分钟` : 'N/A'}
            </p>
          </div>

          {/* Sleep Score */}
          {sleepScore !== null && (
            <div className="flex items-center gap-2">
              <div className={`relative w-16 h-16`}>
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    className="text-muted stroke-current"
                    strokeWidth="4"
                    fill="none"
                  />
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    className={`${qualityInfo.color} stroke-current`}
                    strokeWidth="4"
                    fill="none"
                    strokeDasharray={`${(sleepScore / 100) * 175.93} 175.93`}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <Star className={`h-5 w-5 ${qualityInfo.color}`} fill="currentColor" />
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold">{sleepScore}</p>
                <p className={`text-sm ${qualityInfo.color}`}>{qualityInfo.label}</p>
              </div>
            </div>
          )}
        </div>

        {/* Sleep Stages */}
        <div>
          <p className="text-sm font-medium mb-2">睡眠阶段</p>
          <SleepStagesBar metric={metric} />
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 2: 提交**

```bash
cd frontend
git add components/dashboard/sleep-card.tsx
git commit -m "feat: add enhanced sleep card with quality score"
```

---

## Task 10: 重构工作卡片

**Files:**
- Create: `frontend/components/dashboard/work-card.tsx`

**Step 1: 创建工作卡片组件**

创建 `frontend/components/dashboard/work-card.tsx`:

```typescript
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Clock, Target, Calendar } from 'lucide-react';
import { OverviewMetric } from '@/types/api';
import { CardVisibilityControl } from './card-visibility-control';

interface WorkCardProps {
  metric: OverviewMetric;
  onToggleVisibility: (cardId: string, hidden: boolean) => void;
}

function getActivityHeatmap() {
  // 模拟一天三个时段的工作活跃度（早/中/晚）
  // 实际应用中应从 work_metrics 时间戳聚合计算
  return [
    { period: '早晨', intensity: 30, color: 'bg-orange-300' },
    { period: '下午', intensity: 80, color: 'bg-orange-500' },
    { period: '晚上', intensity: 50, color: 'bg-orange-400' },
  ];
}

export function WorkCard({ metric, onToggleVisibility }: WorkCardProps) {
  const workHours = metric.total_work_minutes
    ? Math.round(metric.total_work_minutes / 60 * 10) / 10
    : null;
  const focusScore = metric.avg_focus_score || null;
  const heatmap = getActivityHeatmap();

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-purple-500" />
          工作数据
        </CardTitle>
        <CardVisibilityControl
          cardId="work"
          isHidden={false}
          onToggle={onToggleVisibility}
        />
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Work Hours */}
        <div>
          <p className="text-sm text-muted-foreground">今日工作时长</p>
          <p className="text-3xl font-bold">
            {workHours ? `${workHours}小时` : 'N/A'}
          </p>
        </div>

        {/* Focus Score */}
        {focusScore !== null && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium flex items-center gap-2">
                <Target className="h-4 w-4 text-purple-500" />
                平均专注度
              </p>
              <span className="text-sm text-muted-foreground">{focusScore}/100</span>
            </div>
            <div className="h-3 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-purple-500 transition-all"
                style={{ width: `${focusScore}%` }}
              />
            </div>
          </div>
        )}

        {/* Activity Heatmap */}
        <div>
          <p className="text-sm font-medium flex items-center gap-2 mb-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            今日活跃时段
          </p>
          <div className="flex gap-2 h-8 rounded-lg overflow-hidden">
            {heatmap.map((slot) => (
              <div
                key={slot.period}
                className="flex-1 flex items-center justify-center text-xs font-medium text-white"
                style={{ backgroundColor: slot.color }}
              >
                {slot.period}
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 2: 提交**

```bash
cd frontend
git add components/dashboard/work-card.tsx
git commit -m "feat: add enhanced work card with focus score and heatmap"
```

---

## Task 11: 重构压力卡片

**Files:**
- Create: `frontend/components/dashboard/stress-card.tsx`

**Step 1: 创建压力卡片组件**

创建 `frontend/components/dashboard/stress-card.tsx`:

```typescript
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Heart, Activity } from 'lucide-react';
import { OverviewMetric } from '@/types/api';
import { CardVisibilityControl } from './card-visibility-control';

interface StressCardProps {
  metric: OverviewMetric;
  onToggleVisibility: (cardId: string, hidden: boolean) => void;
}

function getStressInfo(level: number | null) {
  if (level === null) return { label: '无数据', color: 'bg-gray-400' };

  if (level <= 25) return { label: '平静', color: 'bg-blue-400' };
  if (level <= 50) return { label: '放松', color: 'bg-green-400' };
  if (level <= 75) return { label: '压力', color: 'bg-yellow-400' };
  return { label: '高压力', color: 'bg-red-400' };
}

function getStressColor(level: number) {
  // 从蓝到红的渐变
  if (level <= 25) return 'bg-blue-400';
  if (level <= 50) return 'bg-green-400';
  if (level <= 75) return 'bg-yellow-400';
  return 'bg-red-400';
}

function MiniTrendChart({ currentLevel }: { currentLevel: number }) {
  // 模拟一天的压力趋势（7个数据点代表一天）
  const data = [
    Math.max(0, currentLevel - 10 + Math.random() * 20),
    Math.max(0, currentLevel - 5 + Math.random() * 10),
    currentLevel,
    Math.max(0, currentLevel + Math.random() * 10 - 5),
    Math.max(0, currentLevel + Math.random() * 15 - 5),
    Math.max(0, currentLevel - 10 + Math.random() * 15),
    Math.max(0, currentLevel - 15 + Math.random() * 10),
  ];

  const maxVal = Math.max(...data, 100);
  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * 100;
    const y = 100 - (val / maxVal) * 100;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg viewBox="0 0 100 100" className="w-full h-12">
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        className="text-muted-foreground"
      />
      {data.map((val, i) => {
        const x = (i / (data.length - 1)) * 100;
        const y = 100 - (val / maxVal) * 100;
        return (
          <circle
            key={i}
            cx={x}
            cy={y}
            r="3"
            className={getStressColor(val).replace('bg-', 'fill-')}
          />
        );
      })}
    </svg>
  );
}

export function StressCard({ metric, onToggleVisibility }: StressCardProps) {
  const stressLevel = metric.stress_level;
  const stressInfo = getStressInfo(stressLevel);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="flex items-center gap-2">
          <Heart className="h-5 w-5 text-red-500" />
          压力水平
        </CardTitle>
        <CardVisibilityControl
          cardId="stress"
          isHidden={false}
          onToggle={onToggleVisibility}
        />
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stress Level */}
        {stressLevel !== null ? (
          <>
            <div className="flex items-end justify-between">
              <div>
                <p className="text-sm text-muted-foreground">当前压力水平</p>
                <p className="text-3xl font-bold">{stressLevel}</p>
              </div>
              <div className={`px-3 py-1 rounded-full text-sm font-medium text-white ${stressInfo.color}`}>
                {stressInfo.label}
              </div>
            </div>

            {/* Stress Bar */}
            <div>
              <div className="h-3 rounded-full overflow-hidden bg-gradient-to-r from-blue-400 via-green-400 via-yellow-400 to-red-400">
                <div
                  className="h-full bg-black/20"
                  style={{ width: `${stressLevel}%` }}
                />
              </div>
              <div className="flex justify-between mt-1 text-xs text-muted-foreground">
                <span>平静</span>
                <span>高压力</span>
              </div>
            </div>

            {/* Trend */}
            <div>
              <p className="text-sm font-medium flex items-center gap-2 mb-2">
                <Activity className="h-4 w-4 text-muted-foreground" />
                一日趋势
              </p>
              <MiniTrendChart currentLevel={stressLevel} />
            </div>
          </>
        ) : (
          <p className="text-muted-foreground">暂无压力数据</p>
        )}
      </CardContent>
    </Card>
  );
}
```

**Step 2: 提交**

```bash
cd frontend
git add components/dashboard/stress-card.tsx
git commit -m "feat: add stress card with trend visualization"
```

---

## Task 12: 创建家庭成员横条组件

**Files:**
- Create: `frontend/components/dashboard/family-member-strip.tsx`
- Create: `frontend/components/dashboard/member-detail-panel.tsx`

**Step 1: 创建成员横条组件**

创建 `frontend/components/dashboard/family-member-strip.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { ChevronUp } from 'lucide-react';
import { OverviewMetric } from '@/types/api';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card } from '@/components/ui/card';

interface FamilyMemberStripProps {
  currentUserId: number;
  members: OverviewMetric[];
  onSelectMember: (userId: number) => void;
}

export function FamilyMemberStrip({ currentUserId, members, onSelectMember }: FamilyMemberStripProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const otherMembers = members.filter(m => m.user_id !== currentUserId);

  if (otherMembers.length === 0) {
    return null;
  }

  return (
    <Card className="mt-6">
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium">家庭成员</h3>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-muted rounded"
          >
            <ChevronUp className={`h-4 w-4 transition-transform ${isExpanded ? '' : 'rotate-180'}`} />
          </button>
        </div>

        {!isExpanded ? (
          // Collapsed: horizontal scroll
          <div className="flex gap-3 overflow-x-auto pb-2">
            {otherMembers.map((member) => (
              <FamilyMemberChip
                key={member.user_id}
                member={member}
                onClick={() => onSelectMember(member.user_id)}
              />
            ))}
          </div>
        ) : (
          // Expanded: grid view
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {otherMembers.map((member) => (
              <FamilyMemberCard
                key={member.user_id}
                member={member}
                onClick={() => onSelectMember(member.user_id)}
              />
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

function FamilyMemberChip({
  member,
  onClick
}: {
  member: OverviewMetric;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-muted transition-colors flex-shrink-0"
    >
      <Avatar className="h-8 w-8">
        <AvatarImage src={undefined} />
        <AvatarFallback>{member.user_name.charAt(0)}</AvatarFallback>
      </Avatar>
      <div className="text-left">
        <p className="text-sm font-medium">{member.user_name}</p>
        <p className="text-xs text-muted-foreground">
          睡眠 {member.sleep_hours ? `${member.sleep_hours}h` : 'N/A'}
        </p>
      </div>
    </button>
  );
}

function FamilyMemberCard({
  member,
  onClick
}: {
  member: OverviewMetric;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="p-3 rounded-lg hover:bg-muted transition-colors text-left"
    >
      <div className="flex items-center gap-2 mb-2">
        <Avatar className="h-10 w-10">
          <AvatarFallback>{member.user_name.charAt(0)}</AvatarFallback>
        </Avatar>
        <span className="font-medium">{member.user_name}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <p className="text-muted-foreground text-xs">睡眠</p>
          <p className="font-medium">{member.sleep_hours ? `${member.sleep_hours}h` : 'N/A'}</p>
        </div>
        <div>
          <p className="text-muted-foreground text-xs">运动</p>
          <p className="font-medium">{member.exercise_minutes ? `${member.exercise_minutes}m` : 'N/A'}</p>
        </div>
      </div>
    </button>
  );
}
```

**Step 2: 创建成员详情面板组件**

创建 `frontend/components/dashboard/member-detail-panel.tsx`:

```typescript
'use client';

import { useEffect } from 'react';
import { X } from 'lucide-react';
import { OverviewMetric } from '@/types/api';
import { SleepCard } from './sleep-card';
import { ActivityHealthCard } from './activity-health-card';
import { WorkCard } from './work-card';
import { StressCard } from './stress-card';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface MemberDetailPanelProps {
  member: OverviewMetric | null;
  onClose: () => void;
  onToggleVisibility: (cardId: string, hidden: boolean) => void;
  hiddenCards: string[];
}

export function MemberDetailPanel({
  member,
  onClose,
  onToggleVisibility,
  hiddenCards
}: MemberDetailPanelProps) {
  // Close on Escape key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  if (!member) return null;

  const isCardHidden = (cardId: string) => hiddenCards.includes(cardId);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-4">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-background border-b p-4 flex items-center justify-between">
          <h2 className="text-xl font-bold">{member.user_name} 的详细数据</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="p-4 space-y-4">
          {!isCardHidden('sleep') && (
            <SleepCard metric={member} onToggleVisibility={onToggleVisibility} />
          )}
          {!isCardHidden('activity_health') && (
            <ActivityHealthCard metric={member} onToggleVisibility={onToggleVisibility} />
          )}
          {!isCardHidden('work') && (
            <WorkCard metric={member} onToggleVisibility={onToggleVisibility} />
          )}
          {!isCardHidden('stress') && (
            <StressCard metric={member} onToggleVisibility={onToggleVisibility} />
          )}
        </div>
      </Card>
    </div>
  );
}
```

**Step 3: 提交**

```bash
cd frontend
git add components/dashboard/family-member-strip.tsx components/dashboard/member-detail-panel.tsx
git commit -m "feat: add family member strip and detail panel components"
```

---

## Task 13: 创建卡片设置面板组件

**Files:**
- Create: `frontend/components/dashboard/card-settings-panel.tsx`

**Step 1: 创建卡片设置面板组件**

创建 `frontend/components/dashboard/card-settings-panel.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { X, Check } from 'lucide-react';
import { CardId, CARD_IDS } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface CardSettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  hiddenCards: string[];
  onToggleCard: (cardId: string, hidden: boolean) => void;
}

const CARD_LABELS: Record<CardId, { name: string; icon: string }> = {
  [CARD_IDS.SLEEP]: { name: '睡眠分析', icon: '😴' },
  [CARD_IDS.ACTIVITY_HEALTH]: { name: '运动与健康', icon: '💪' },
  [CARD_IDS.WORK]: { name: '工作数据', icon: '💼' },
  [CARD_IDS.STRESS]: { name: '压力水平', icon: '❤️' },
  [CARD_IDS.TRENDS]: { name: '趋势图表', icon: '📈' },
};

export function CardSettingsPanel({
  isOpen,
  onClose,
  hiddenCards,
  onToggleCard
}: CardSettingsPanelProps) {
  if (!isOpen) return null;

  const allCardIds: CardId[] = Object.values(CARD_IDS);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <div className="p-4 border-b flex items-center justify-between">
          <h3 className="font-bold text-lg">显示设置</h3>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="p-4 space-y-2">
          <p className="text-sm text-muted-foreground mb-4">
            选择要在首页显示的卡片
          </p>

          {allCardIds.map((cardId) => {
            const isHidden = hiddenCards.includes(cardId);
            const card = CARD_LABELS[cardId];

            return (
              <button
                key={cardId}
                onClick={() => onToggleCard(cardId, !isHidden)}
                className={`w-full p-3 rounded-lg flex items-center justify-between transition-colors ${
                  isHidden ? 'bg-muted opacity-60' : 'bg-primary/5 hover:bg-primary/10'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{card.icon}</span>
                  <span className="font-medium">{card.name}</span>
                </div>
                {!isHidden && (
                  <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center">
                    <Check className="h-4 w-4 text-primary-foreground" />
                  </div>
                )}
              </button>
            );
          })}
        </div>

        <div className="p-4 border-t">
          <Button onClick={onClose} className="w-full">
            完成
          </Button>
        </div>
      </Card>
    </div>
  );
}
```

**Step 2: 提交**

```bash
cd frontend
git add components/dashboard/card-settings-panel.tsx
git commit -m "feat: add card settings panel for visibility control"
```

---

## Task 14: 更新主页面使用新组件

**Files:**
- Modify: `frontend/app/page.tsx`

**Step 1: 重构主页面**

完全重写 `frontend/app/page.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { ProtectedRoute } from '@/components/protected-route';
import { SiteHeader } from '@/components/site-header';
import { getOverview, getTrends, getDashboardSummary, updateHiddenCards } from '@/lib/api';
import { OverviewResponse, TrendResponse, SummaryResponse, CardId } from '@/types/api';
import { UserSummaryCard } from '@/components/dashboard/user-summary-card';
import { SleepCard } from '@/components/dashboard/sleep-card';
import { ActivityHealthCard } from '@/components/dashboard/activity-health-card';
import { WorkCard } from '@/components/dashboard/work-card';
import { StressCard } from '@/components/dashboard/stress-card';
import { TrendChart } from '@/components/trend-chart';
import { FamilyMemberStrip } from '@/components/dashboard/family-member-strip';
import { MemberDetailPanel } from '@/components/dashboard/member-detail-panel';
import { CardSettingsPanel } from '@/components/dashboard/card-settings-panel';
import { RefreshCw, Settings } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

export default function DashboardPage() {
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [trends, setTrends] = useState<TrendResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Card visibility
  const [hiddenCards, setHiddenCards] = useState<string[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Member detail panel
  const [selectedMember, setSelectedMember] = useState<OverviewMetric | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const [summaryData, overviewData, trendsData] = await Promise.all([
        getDashboardSummary(),
        getOverview(),
        getTrends(30),
      ]);

      setSummary(summaryData);
      setOverview(overviewData);
      setTrends(trendsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleToggleCard = async (cardId: string, hidden: boolean) => {
    const newHiddenCards = hidden
      ? [...hiddenCards, cardId]
      : hiddenCards.filter(id => id !== cardId);

    setHiddenCards(newHiddenCards);

    // Persist to backend
    try {
      await updateHiddenCards(JSON.stringify(newHiddenCards));
    } catch (err) {
      console.error('Failed to update hidden cards:', err);
      // Revert on error
      setHiddenCards(hiddenCards);
    }
  };

  const isCardHidden = (cardId: string) => hiddenCards.includes(cardId);

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen">
          <SiteHeader />
          <main className="container mx-auto py-8">
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4" />
                <p className="text-muted-foreground">Loading dashboard...</p>
              </div>
            </div>
          </main>
        </div>
      </ProtectedRoute>
    );
  }

  if (error) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen">
          <SiteHeader />
          <main className="container mx-auto py-8">
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <p className="text-red-500 mb-4">Error: {error}</p>
                <button
                  onClick={fetchData}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
                >
                  Retry
                </button>
              </div>
            </div>
          </main>
        </div>
      </ProtectedRoute>
    );
  }

  if (!summary || !overview) {
    return null;
  }

  // Get current user's metrics from overview
  const currentUserMetrics = overview.metrics.find(m => m.user_id === summary.user_id);
  if (!currentUserMetrics) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen">
          <SiteHeader />
          <main className="container mx-auto py-8">
            <p className="text-center text-muted-foreground">No data available</p>
          </main>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen">
        <SiteHeader />
        <main className="container mx-auto py-8 space-y-6">
          {/* Header with settings button */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold tracking-tight">Dashboard</h1>
              <p className="text-muted-foreground">
                Track and analyze your health and work patterns
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setSettingsOpen(true)}
                className="flex items-center gap-2 px-4 py-2 border rounded-md hover:bg-muted"
              >
                <Settings className="h-4 w-4" />
                显示设置
              </button>
              <button
                onClick={fetchData}
                className="flex items-center gap-2 px-4 py-2 border rounded-md hover:bg-muted"
              >
                <RefreshCw className="h-4 w-4" />
                刷新
              </button>
            </div>
          </div>

          {/* User Summary Card */}
          <UserSummaryCard summary={summary} />

          {/* Dashboard Cards Grid */}
          {!isCardHidden('sleep') && (
            <SleepCard metric={currentUserMetrics} onToggleVisibility={handleToggleCard} />
          )}

          {!isCardHidden('activity_health') && (
            <ActivityHealthCard metric={currentUserMetrics} onToggleVisibility={handleToggleCard} />
          )}

          {!isCardHidden('work') && (
            <WorkCard metric={currentUserMetrics} onToggleVisibility={handleToggleCard} />
          )}

          {!isCardHidden('stress') && (
            <StressCard metric={currentUserMetrics} onToggleVisibility={handleToggleCard} />
          )}

          {!isCardHidden('trends') && trends && trends.data.length > 0 && (
            <Card>
              <CardContent className="pt-6">
                <TrendChart
                  data={trends.data}
                  startDate={trends.start_date}
                  endDate={trends.end_date}
                />
              </CardContent>
            </Card>
          )}

          {/* Family Member Strip */}
          <FamilyMemberStrip
            currentUserId={summary.user_id}
            members={overview.metrics}
            onSelectMember={(userId) => {
              const member = overview.metrics.find(m => m.user_id === userId);
              if (member) setSelectedMember(member);
            }}
          />
        </main>

        {/* Member Detail Panel */}
        <MemberDetailPanel
          member={selectedMember}
          onClose={() => setSelectedMember(null)}
          onToggleVisibility={handleToggleCard}
          hiddenCards={hiddenCards}
        />

        {/* Card Settings Panel */}
        <CardSettingsPanel
          isOpen={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          hiddenCards={hiddenCards}
          onToggleCard={handleToggleCard}
        />
      </div>
    </ProtectedRoute>
  );
}
```

**Step 2: 提交**

```bash
cd frontend
git add app/page.tsx
git commit -m "feat: redesign dashboard page with new card components"
```

---

## Task 15: 删除或归档旧组件

**Files:**
- Remove: `frontend/components/overview-panel.tsx`
- Remove: `frontend/components/preference-settings.tsx`

**Step 1: 删除旧组件**

```bash
cd frontend
rm components/overview-panel.tsx
rm components/preference-settings.tsx
```

**Step 2: 提交**

```bash
cd frontend
git add -A
git commit -m "chore: remove old overview-panel and preference-settings components

Replaced by new dashboard card components"
```

---

## Task 16: 更新佳明同步逻辑以支持新字段

**Files:**
- Modify: `backend/app/api/v1/garmin.py` (sync endpoint)

**Step 1: 更新佳明同步时的数据映射**

在佳明同步逻辑中，添加对新字段的处理：

```python
# 在 Garmin 同步处理中，添加以下字段映射
health_data.update({
    'steps': daily_data.get('steps'),  # 从佳明 API 获取
    'calories': daily_data.get('calories'),
    'distance_km': daily_data.get('distance', 0) / 1000,  # 转换米到公里
    'body_battery': daily_data.get('body_battery'),
    'spo2': daily_data.get('spo2'),
    'respiration_rate': daily_data.get('respiration'),
    'resting_hr': daily_data.get('resting_heart_rate'),
    'sleep_score': daily_data.get('sleep_score'),
})
```

**注意**: 具体字段名需要根据 garmin-connect API 实际返回的数据结构调整。

**Step 2: 提交**

```bash
cd backend
git add app/api/v1/garmin.py
git commit -m "feat: update Garmin sync to populate new health metric fields"
```

---

## Task 17: 最终测试与验证

**Files:** None (testing)

**Step 1: 启动后端服务**

```bash
cd backend
python main.py
```

**Step 2: 启动前端服务**

```bash
cd frontend
npm run dev
```

**Step 3: 测试清单**

在浏览器中访问 `http://localhost:3000` 并验证：

- [ ] 页面加载正常，显示当前用户的摘要卡片
- [ ] 睡眠卡片显示睡眠时长、质量评分和阶段条
- [ ] 运动/健康卡片可以切换 Tab，显示各自内容
- [ ] 工作卡片显示工作时长和专注度
- [ ] 压力卡片显示压力水平和趋势
- [ ] 点击卡片右上角眼睛图标可以隐藏卡片
- [ ] 点击"显示设置"按钮打开设置面板
- [ ] 在设置面板中可以恢复已隐藏的卡片
- [ ] 家庭成员横条显示其他成员
- [ ] 点击成员小卡片打开详情面板
- [ ] 刷新页面后卡片可见性状态保持
- [ ] 响应式布局在移动设备正常显示

**Step 4: 修复发现的问题**

记录并修复测试中发现的问题。

**Step 5: 最终提交**

```bash
# Backend
cd backend
git add -A
git commit -m "test: final testing and bug fixes for dashboard redesign"

# Frontend
cd frontend
git add -A
git commit -m "test: final testing and bug fixes for dashboard redesign"
```

---

## 实施完成后的清理工作

1. **更新文档**: 更新 `CLAUDE.md` 和 `README.md` 中的架构说明
2. **数据库迁移脚本**: 为生产环境创建 Alembic 迁移脚本
3. **API 文档**: 确保新端点在 Swagger UI 中正确显示

---

## 验收标准

- [ ] 所有后端 API 测试通过
- [ ] 所有前端组件正常渲染
- [ ] 卡片可见性状态持久化
- [ ] 响应式设计在各屏幕尺寸正常
- [ ] 无 TypeScript 错误
- [ ] 无 ESLint 警告

---

**实施总工时估计**: 6-8 小时
**测试时间**: 1-2 小时
