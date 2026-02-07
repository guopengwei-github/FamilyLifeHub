'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { CardVisibilityControl } from '@/components/dashboard/card-visibility-control';
import { OverviewMetric } from '@/types/api';
import {
  Flame,
  Footprints,
  Clock,
  Route,
  Battery,
  Droplets,
  Wind,
  HeartPulse,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ActivityHealthCardProps {
  metrics: OverviewMetric[];
  hiddenCards?: Set<string>;
  onToggleCard?: (cardId: string, hidden: boolean) => void;
  className?: string;
}

interface MetricItemProps {
  icon: React.ElementType;
  value: number | null;
  unit: string;
  label: string;
  color: string;
  maxValue?: number;
}

function MetricItem({
  icon: Icon,
  value,
  unit,
  label,
  color,
  maxValue = 100,
}: MetricItemProps) {
  const displayValue = value ?? null;
  const progressPercent = displayValue ? Math.min((displayValue / maxValue) * 100, 100) : 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className={cn('h-4 w-4', color)} />
          <span className="text-sm font-medium">{label}</span>
        </div>
        <span className="text-sm text-muted-foreground">
          {displayValue !== null ? `${displayValue}${unit}` : 'N/A'}
        </span>
      </div>
      <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-300', color.replace('text-', 'bg-'))}
          style={{ width: `${progressPercent}%` }}
        />
      </div>
    </div>
  );
}

export function ActivityHealthCard({
  metrics,
  hiddenCards = new Set(),
  onToggleCard,
  className = '',
}: ActivityHealthCardProps) {
  const [activeTab, setActiveTab] = useState<'activity' | 'health'>('activity');
  const isHidden = hiddenCards.has('activity_health');

  if (isHidden) {
    return (
      <Card className={cn('opacity-50', className)}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">运动/健康卡片已隐藏</span>
            {onToggleCard && (
              <CardVisibilityControl
                cardId="activity_health"
                isHidden={true}
                onToggle={onToggleCard}
              />
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  // 计算所有用户的平均值
  const calculateAverage = (getValue: (metric: OverviewMetric) => number | null) => {
    const values = metrics.map(getValue).filter((v): v is number => v !== null);
    return values.length > 0 ? Math.round(values.reduce((a, b) => a + b, 0) / values.length) : null;
  };

  // 计算平均值，保留一位小数
  const calculateAverageOneDecimal = (getValue: (metric: OverviewMetric) => number | null) => {
    const values = metrics.map(getValue).filter((v): v is number => v !== null);
    if (values.length === 0) return null;
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    return Math.round(avg * 10) / 10;
  };

  // 运动 Tab 数据
  const activityMetrics = {
    calories: calculateAverage((metric) => metric.calories ?? null),
    steps: calculateAverage((metric) => metric.steps ?? null),
    activeMinutes: calculateAverage((metric) => metric.exercise_minutes ?? null),
    distance: calculateAverageOneDecimal((metric) => metric.distance_km ?? null),
  };

  // 健康 Tab 数据
  const healthMetrics = {
    bodyBattery: calculateAverage((metric) => metric.body_battery ?? null),
    spo2: calculateAverage((metric) => metric.spo2 ?? null),
    respirationRate: calculateAverage((metric) => metric.respiration_rate ?? null),
    restingHr: calculateAverage((metric) => metric.resting_hr ?? null),
  };

  const activityItems: MetricItemProps[] = [
    {
      icon: Flame,
      value: activityMetrics.calories,
      unit: ' kcal',
      label: '卡路里',
      color: 'text-orange-500',
      maxValue: 500,
    },
    {
      icon: Footprints,
      value: activityMetrics.steps,
      unit: ' 步',
      label: '步数',
      color: 'text-green-500',
      maxValue: 10000,
    },
    {
      icon: Clock,
      value: activityMetrics.activeMinutes,
      unit: ' 分钟',
      label: '活动时长',
      color: 'text-blue-500',
      maxValue: 120,
    },
    {
      icon: Route,
      value: activityMetrics.distance,
      unit: ' km',
      label: '距离',
      color: 'text-purple-500',
      maxValue: 20,
    },
  ];

  const healthItems: MetricItemProps[] = [
    {
      icon: Battery,
      value: healthMetrics.bodyBattery,
      unit: '',
      label: '身体电量',
      color: 'text-green-500',
      maxValue: 100,
    },
    {
      icon: Droplets,
      value: healthMetrics.spo2,
      unit: '%',
      label: '血氧饱和度',
      color: 'text-blue-500',
      maxValue: 100,
    },
    {
      icon: Wind,
      value: healthMetrics.respirationRate,
      unit: '/分',
      label: '呼吸频率',
      color: 'text-cyan-500',
      maxValue: 30,
    },
    {
      icon: HeartPulse,
      value: healthMetrics.restingHr,
      unit: ' bpm',
      label: '静息心率',
      color: 'text-red-500',
      maxValue: 100,
    },
  ];

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>运动 & 健康</CardTitle>
          {onToggleCard && (
            <CardVisibilityControl
              cardId="activity_health"
              isHidden={false}
              onToggle={onToggleCard}
            />
          )}
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'activity' | 'health')}>
          <TabsList className="w-full">
            <TabsTrigger value="activity" className="flex-1">
              运动
            </TabsTrigger>
            <TabsTrigger value="health" className="flex-1">
              健康
            </TabsTrigger>
          </TabsList>

          <TabsContent value="activity" className="space-y-4">
            {activityItems.map((item) => (
              <MetricItem key={item.label} {...item} />
            ))}
          </TabsContent>

          <TabsContent value="health" className="space-y-4">
            {healthItems.map((item) => (
              <MetricItem key={item.label} {...item} />
            ))}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
