'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CardVisibilityControl } from '@/components/dashboard/card-visibility-control';
import { OverviewMetric } from '@/types/api';
import { Clock, Target, Calendar } from 'lucide-react';
import { cn } from '@/lib/utils';

interface WorkCardProps {
  metrics: OverviewMetric[];
  hiddenCards?: Set<string>;
  onToggleCard?: (cardId: string, hidden: boolean) => void;
  className?: string;
}

interface ProgressBarProps {
  value: number;
  max: number;
  label: string;
  color: string;
  unit?: string;
}

function ProgressBar({ value, max, label, color, unit = '' }: ProgressBarProps) {
  const percentage = max > 0 ? Math.min((value / max) * 100, 100) : 0;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">
          {value.toFixed(1)}
          {unit}
        </span>
      </div>
      <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-300', color)}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

interface TimeSlotHeatmapProps {
  morning: number; // 6-12
  afternoon: number; // 12-18
  evening: number; // 18-24
  maxIntensity?: number;
}

function TimeSlotHeatmap({
  morning,
  afternoon,
  evening,
  maxIntensity = 100,
}: TimeSlotHeatmapProps) {
  const getIntensityColor = (value: number) => {
    const intensity = Math.min(value / maxIntensity, 1);
    if (intensity === 0) return 'bg-gray-200 dark:bg-gray-800';
    if (intensity < 0.33) return 'bg-green-200 dark:bg-green-900';
    if (intensity < 0.66) return 'bg-yellow-200 dark:bg-yellow-900';
    return 'bg-red-200 dark:bg-red-900';
  };

  const slots = [
    { label: '上午', value: morning, icon: '🌅' },
    { label: '下午', value: afternoon, icon: '☀️' },
    { label: '晚上', value: evening, icon: '🌙' },
  ];

  return (
    <div className="space-y-3">
      <div className="flex gap-2 h-20">
        {slots.map((slot) => (
          <div
            key={slot.label}
            className={cn(
              'flex-1 rounded-lg flex flex-col items-center justify-center p-2 transition-all',
              getIntensityColor(slot.value)
            )}
          >
            <span className="text-2xl mb-1">{slot.icon}</span>
            <span className="text-xs font-medium">{slot.label}</span>
            <span className="text-lg font-bold">{slot.value}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground text-center">
        今日活跃时段分布 (小时)
      </p>
    </div>
  );
}

export function WorkCard({
  metrics,
  hiddenCards = new Set(),
  onToggleCard,
  className = '',
}: WorkCardProps) {
  const isHidden = hiddenCards.has('work');

  if (isHidden) {
    return (
      <Card className={cn('opacity-50', className)}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">工作卡片已隐藏</span>
            {onToggleCard && (
              <CardVisibilityControl
                cardId="work"
                isHidden={true}
                onToggle={onToggleCard}
              />
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Calculate average metrics across all users
  const calculateAverage = (getValue: (metric: OverviewMetric) => number | null) => {
    const values = metrics.map(getValue).filter((v): v is number => v !== null);
    return values.length > 0
      ? values.reduce((a, b) => a + b, 0) / values.length
      : null;
  };

  const avgWorkMinutes = calculateAverage((m) => m.total_work_minutes ?? null);
  const avgWorkHours = avgWorkMinutes ? avgWorkMinutes / 60 : 0;
  const avgFocusScore = calculateAverage((m) => m.avg_focus_score ?? null);

  // Simulated time slot distribution (in a real app, this would come from detailed metrics)
  const timeSlotData = {
    morning: avgWorkHours > 0 ? Math.min(avgWorkHours * 0.4, 4) : 0,
    afternoon: avgWorkHours > 0 ? Math.min(avgWorkHours * 0.4, 4) : 0,
    evening: avgWorkHours > 0 ? Math.min(avgWorkHours * 0.2, 3) : 0,
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-blue-500" />
            <CardTitle>工作数据</CardTitle>
          </div>
          {onToggleCard && (
            <CardVisibilityControl
              cardId="work"
              isHidden={false}
              onToggle={onToggleCard}
            />
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left: Work Hours and Focus Score */}
          <div className="space-y-6">
            {/* Work Hours Progress */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-blue-500" />
                <span className="text-sm font-medium">今日工作时长</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold">
                  {avgWorkHours > 0 ? avgWorkHours.toFixed(1) : '0.0'}
                </span>
                <span className="text-muted-foreground">小时</span>
              </div>
              <ProgressBar
                value={avgWorkHours}
                max={8}
                label="每日目标进度"
                color="bg-blue-500"
                unit=" / 8h"
              />
            </div>

            {/* Focus Score Progress */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-purple-500" />
                <span className="text-sm font-medium">平均专注度</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold">
                  {avgFocusScore ? Math.round(avgFocusScore) : 'N/A'}
                </span>
                <span className="text-muted-foreground">/ 100</span>
              </div>
              <ProgressBar
                value={avgFocusScore ?? 0}
                max={100}
                label="专注度评分"
                color="bg-purple-500"
              />
            </div>
          </div>

          {/* Right: Active Time Slots Heatmap */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-green-500" />
              <span className="text-sm font-medium">活跃时段分布</span>
            </div>
            <TimeSlotHeatmap
              morning={timeSlotData.morning}
              afternoon={timeSlotData.afternoon}
              evening={timeSlotData.evening}
              maxIntensity={4}
            />

            {/* Quick Stats */}
            <div className="grid grid-cols-3 gap-2 pt-2">
              <div className="text-center p-2 rounded-lg bg-muted">
                <div className="text-xs text-muted-foreground">总时长</div>
                <div className="font-semibold">{avgWorkHours.toFixed(1)}h</div>
              </div>
              <div className="text-center p-2 rounded-lg bg-muted">
                <div className="text-xs text-muted-foreground">专注度</div>
                <div className="font-semibold">{avgFocusScore ? Math.round(avgFocusScore) : '-'}</div>
              </div>
              <div className="text-center p-2 rounded-lg bg-muted">
                <div className="text-xs text-muted-foreground">效率</div>
                <div className="font-semibold">
                  {avgFocusScore && avgWorkHours > 0
                    ? Math.round(avgFocusScore * avgWorkHours / 8)
                    : '-'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
