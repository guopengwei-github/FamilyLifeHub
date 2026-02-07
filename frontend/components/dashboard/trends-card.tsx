'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CardVisibilityControl } from '@/components/dashboard/card-visibility-control';
import { TrendResponse, DailyTrendData } from '@/types/api';
import { TrendingUp, Calendar } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TrendsCardProps {
  trends: TrendResponse | null;
  hiddenCards?: Set<string>;
  onToggleCard?: (cardId: string, hidden: boolean) => void;
  className?: string;
}

interface MiniSparklineProps {
  data: number[];
  color: string;
  height?: number;
}

function MiniSparkline({ data, color = '#8b5cf6', height = 40 }: MiniSparklineProps) {
  if (data.length === 0) return null;

  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;

  const points = data
    .map((value, index) => {
      const x = (index / (data.length - 1)) * 100;
      const y = 100 - ((value - min) / range) * 80 - 10;
      return `${x},${y}`;
    })
    .join(' ');

  const areaPoints = `0,100 ${points} 100,100`;

  return (
    <svg viewBox="0 0 100 100" className="w-full h-full" preserveAspectRatio="none">
      <polygon
        points={areaPoints}
        fill={color}
        fillOpacity="0.15"
      />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

interface MetricTrendItemProps {
  label: string;
  currentValue: number | null;
  previousValue: number | null;
  unit: string;
  color: string;
  icon: string;
}

function MetricTrendItem({
  label,
  currentValue,
  previousValue,
  unit,
  color,
  icon,
}: MetricTrendItemProps) {
  const change = currentValue !== null && previousValue !== null
    ? currentValue - previousValue
    : null;

  const changePercent = change !== null && previousValue !== null && previousValue !== 0
    ? (change / previousValue) * 100
    : null;

  const isPositive = change !== null && change > 0;

  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
      <div className="flex items-center gap-3">
        <span className="text-xl">{icon}</span>
        <div>
          <p className="text-sm font-medium">{label}</p>
          <p className="text-xs text-muted-foreground">
            {currentValue !== null ? `${currentValue.toFixed(1)}${unit}` : 'N/A'}
          </p>
        </div>
      </div>
      <div className="text-right">
        {changePercent !== null ? (
          <div className={cn(
            'flex items-center gap-1 text-sm font-medium',
            isPositive ? 'text-green-500' : changePercent < 0 ? 'text-red-500' : 'text-muted-foreground'
          )}>
            <TrendingUp className={cn('h-3 w-3', changePercent < 0 && 'rotate-180')} />
            {Math.abs(changePercent).toFixed(1)}%
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">-</span>
        )}
        <p className="text-xs text-muted-foreground">vs 上周</p>
      </div>
    </div>
  );
}

export function TrendsCard({
  trends,
  hiddenCards = new Set(),
  onToggleCard,
  className = '',
}: TrendsCardProps) {
  const isHidden = hiddenCards.has('trends');

  if (isHidden) {
    return (
      <Card className={cn('opacity-50', className)}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">趋势图表已隐藏</span>
            {onToggleCard && (
              <CardVisibilityControl
                cardId="trends"
                isHidden={true}
                onToggle={onToggleCard}
              />
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Calculate weekly averages from trends data
  const calculateWeeklyAverage = (getValue: (d: DailyTrendData) => number | null) => {
    if (!trends || trends.data.length === 0) return null;

    const values = trends.data.map(getValue).filter((v): v is number => v !== null);
    return values.length > 0
      ? values.reduce((a, b) => a + b, 0) / values.length
      : null;
  };

  // Calculate previous week average (last 7 days before current week)
  const calculatePreviousWeekAverage = (getValue: (d: DailyTrendData) => number | null) => {
    if (!trends || trends.data.length < 14) return null;

    const previousWeekData = trends.data.slice(7, 14);
    const values = previousWeekData.map(getValue).filter((v): v is number => v !== null);
    return values.length > 0
      ? values.reduce((a, b) => a + b, 0) / values.length
      : null;
  };

  const currentWeekSleep = calculateWeeklyAverage((d) => d.sleep_hours ?? null);
  const previousWeekSleep = calculatePreviousWeekAverage((d) => d.sleep_hours ?? null);

  const currentWeekExercise = calculateWeeklyAverage((d) => d.exercise_minutes ?? null);
  const previousWeekExercise = calculatePreviousWeekAverage((d) => d.exercise_minutes ?? null);

  const currentWeekStress = calculateWeeklyAverage((d) => d.stress_level ?? null);
  const previousWeekStress = calculatePreviousWeekAverage((d) => d.stress_level ?? null);

  const currentWeekWork = calculateWeeklyAverage((d) => (d.total_work_minutes ?? null) ? (d.total_work_minutes! / 60) : null);
  const previousWeekWork = calculatePreviousWeekAverage((d) => (d.total_work_minutes ?? null) ? (d.total_work_minutes! / 60) : null);

  // Get trend line data for the chart
  const getTrendLine = (getValue: (d: DailyTrendData) => number | null, count = 14) => {
    if (!trends || trends.data.length === 0) return [];
    const recent = trends.data.slice(0, count);
    return recent.map(getValue).filter((v): v is number => v !== null);
  };

  const sleepTrend = getTrendLine((d) => d.sleep_hours ?? null);
  const exerciseTrend = getTrendLine((d) => d.exercise_minutes ?? null);
  const stressTrend = getTrendLine((d) => d.stress_level ?? null);
  const workTrend = getTrendLine((d) => (d.total_work_minutes ?? null) ? (d.total_work_minutes! / 60) : null);

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-purple-500" />
            <CardTitle>趋势图表</CardTitle>
          </div>
          {onToggleCard && (
            <CardVisibilityControl
              cardId="trends"
              isHidden={false}
              onToggle={onToggleCard}
            />
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Date Range Info */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Calendar className="h-4 w-4" />
            {trends ? (
              <span>
                {new Date(trends.start_date).toLocaleDateString('zh-CN')} - {new Date(trends.end_date).toLocaleDateString('zh-CN')}
              </span>
            ) : (
              <span>加载数据中...</span>
            )}
          </div>

          {/* Mini Sparklines */}
          {trends && trends.data.length > 0 ? (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Sleep Trend */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">睡眠</span>
                  <span className="text-sm font-medium">
                    {currentWeekSleep ? `${currentWeekSleep.toFixed(1)}h` : 'N/A'}
                  </span>
                </div>
                <div className="h-12">
                  <MiniSparkline data={sleepTrend} color="#6366f1" />
                </div>
              </div>

              {/* Exercise Trend */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">运动</span>
                  <span className="text-sm font-medium">
                    {currentWeekExercise ? `${currentWeekExercise.toFixed(0)}m` : 'N/A'}
                  </span>
                </div>
                <div className="h-12">
                  <MiniSparkline data={exerciseTrend} color="#22c55e" />
                </div>
              </div>

              {/* Stress Trend */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">压力</span>
                  <span className="text-sm font-medium">
                    {currentWeekStress ? `${Math.round(currentWeekStress)}` : 'N/A'}
                  </span>
                </div>
                <div className="h-12">
                  <MiniSparkline data={stressTrend} color="#ef4444" />
                </div>
              </div>

              {/* Work Trend */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">工作</span>
                  <span className="text-sm font-medium">
                    {currentWeekWork ? `${currentWeekWork.toFixed(1)}h` : 'N/A'}
                  </span>
                </div>
                <div className="h-12">
                  <MiniSparkline data={workTrend} color="#3b82f6" />
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              暂无趋势数据
            </div>
          )}

          {/* Week-over-week comparison */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium">周度对比</h3>

            <MetricTrendItem
              label="平均睡眠"
              currentValue={currentWeekSleep}
              previousValue={previousWeekSleep}
              unit="h"
              color="#6366f1"
              icon="😴"
            />

            <MetricTrendItem
              label="平均运动"
              currentValue={currentWeekExercise}
              previousValue={previousWeekExercise}
              unit="m"
              color="#22c55e"
              icon="🏃"
            />

            <MetricTrendItem
              label="平均压力"
              currentValue={currentWeekStress}
              previousValue={previousWeekStress}
              unit=""
              color="#ef4444"
              icon="❤️"
            />

            <MetricTrendItem
              label="平均工作"
              currentValue={currentWeekWork}
              previousValue={previousWeekWork}
              unit="h"
              color="#3b82f6"
              icon="💼"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
