'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CardVisibilityControl } from '@/components/dashboard/card-visibility-control';
import { OverviewMetric, GarminActivity } from '@/types/api';
import { Flame, Footprints, Clock, Route, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getGarminActivities } from '@/lib/api';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface ActivityCardProps {
  metrics: OverviewMetric[];
  userId?: number;
  date?: string;
  hiddenCards?: Set<string>;
  onToggleCard?: (cardId: string, hidden: boolean) => void;
  className?: string;
}

interface MetricItemProps {
  icon: React.ElementType;
  value: number | string | null;
  unit: string;
  label: string;
  color: string;
}

function MetricItem({ icon: Icon, value, unit, label, color }: MetricItemProps) {
  return (
    <div className="flex flex-col items-center p-3 bg-muted/50 rounded-lg">
      <Icon className={cn('h-5 w-5 mb-1', color)} />
      <span className="text-lg font-semibold">
        {value !== null ? `${value}${unit}` : 'N/A'}
      </span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

const ACTIVITY_ICONS: Record<string, string> = {
  running: '🏃',
  cycling: '🚴',
  swimming: '🏊',
  walking: '🚶',
  strength_training: '💪',
  hiking: '🥾',
  yoga: '🧘',
  other: '🏋️',
};

function getActivityIcon(activityType: string | null): string {
  if (!activityType) return '🏋️';
  const key = activityType.toLowerCase().replace(/\s+/g, '_');
  return ACTIVITY_ICONS[key] || '🏋️';
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return 'N/A';
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}分钟`;
  const hours = Math.floor(mins / 60);
  const remainMins = mins % 60;
  return `${hours}小时${remainMins}分`;
}

function formatDistance(meters: number | null): string {
  if (!meters) return 'N/A';
  const km = meters / 1000;
  return km >= 1 ? `${km.toFixed(1)}km` : `${meters}m`;
}

function formatPace(speedMps: number | null, activityType: string | null): string {
  if (!speedMps || speedMps === 0) return '';

  const isRunning = activityType?.toLowerCase().includes('running') ||
                    activityType?.toLowerCase().includes('walking');

  if (isRunning) {
    const paceSecsPerKm = 1000 / speedMps;
    const mins = Math.floor(paceSecsPerKm / 60);
    const secs = Math.floor(paceSecsPerKm % 60);
    return `配速${mins}'${secs.toString().padStart(2, '0')}"`;
  } else {
    const kmh = speedMps * 3.6;
    return `${kmh.toFixed(1)}km/h`;
  }
}

export function ActivityCard({
  metrics,
  userId,
  date,
  hiddenCards = new Set(),
  onToggleCard,
  className = '',
}: ActivityCardProps) {
  const [activities, setActivities] = useState<GarminActivity[]>([]);
  const [loadingActivities, setLoadingActivities] = useState(false);
  const isHidden = hiddenCards.has('activity');

  useEffect(() => {
    if (userId && date) {
      setLoadingActivities(true);
      getGarminActivities(userId, date)
        .then((res) => setActivities(res.activities))
        .catch(() => setActivities([]))
        .finally(() => setLoadingActivities(false));
    }
  }, [userId, date]);

  if (isHidden) {
    return (
      <Card className={cn('opacity-50', className)}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">运动卡片已隐藏</span>
            {onToggleCard && (
              <CardVisibilityControl cardId="activity" isHidden={true} onToggle={onToggleCard} />
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  const calculateAverage = (getValue: (m: OverviewMetric) => number | null) => {
    const values = metrics.map(getValue).filter((v): v is number => v !== null);
    return values.length > 0 ? Math.round(values.reduce((a, b) => a + b, 0) / values.length) : null;
  };

  const calculateAverageOneDecimal = (getValue: (m: OverviewMetric) => number | null) => {
    const values = metrics.map(getValue).filter((v): v is number => v !== null);
    if (values.length === 0) return null;
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    return Math.round(avg * 10) / 10;
  };

  const activityMetrics = {
    steps: calculateAverage((m) => m.steps ?? null),
    calories: calculateAverage((m) => m.calories ?? null),
    distance: calculateAverageOneDecimal((m) => m.distance_km ?? null),
    activeMinutes: calculateAverage((m) => m.exercise_minutes ?? null),
  };

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-green-500" />
            运动
          </CardTitle>
          {onToggleCard && (
            <CardVisibilityControl cardId="activity" isHidden={false} onToggle={onToggleCard} />
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 今日汇总 */}
        <div className="grid grid-cols-4 gap-2">
          <MetricItem
            icon={Footprints}
            value={activityMetrics.steps?.toLocaleString() ?? null}
            unit=""
            label="步数"
            color="text-green-500"
          />
          <MetricItem
            icon={Flame}
            value={activityMetrics.calories}
            unit=""
            label="卡路里"
            color="text-orange-500"
          />
          <MetricItem
            icon={Route}
            value={activityMetrics.distance}
            unit="km"
            label="距离"
            color="text-purple-500"
          />
          <MetricItem
            icon={Clock}
            value={activityMetrics.activeMinutes}
            unit="分"
            label="时长"
            color="text-blue-500"
          />
        </div>

        {/* 最近活动 */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">最近活动</h4>
          {loadingActivities ? (
            <div className="text-sm text-muted-foreground text-center py-4">加载中...</div>
          ) : activities.length === 0 ? (
            <div className="text-sm text-muted-foreground text-center py-4 space-y-2">
              <p>暂无单独活动记录</p>
              <p className="text-xs">今日运动数据已记录在上方汇总中</p>
            </div>
          ) : (
            <div className="space-y-2">
              {activities.slice(0, 3).map((activity) => (
                <div
                  key={activity.id}
                  className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg"
                >
                  <span className="text-2xl">{getActivityIcon(activity.activity_type)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">
                        {activity.name || activity.activity_type || '活动'}
                      </span>
                      {activity.start_time_local && (
                        <span className="text-xs text-muted-foreground">
                          {format(new Date(activity.start_time_local), 'HH:mm', { locale: zhCN })}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground flex flex-wrap gap-2">
                      <span>{formatDistance(activity.distance_meters)}</span>
                      <span>·</span>
                      <span>{formatDuration(activity.duration_seconds)}</span>
                      {activity.average_heartrate && (
                        <>
                          <span>·</span>
                          <span>心率{activity.average_heartrate}</span>
                        </>
                      )}
                      {activity.avg_speed_mps && (
                        <>
                          <span>·</span>
                          <span>{formatPace(activity.avg_speed_mps, activity.activity_type)}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
