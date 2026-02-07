'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CardVisibilityControl } from '@/components/dashboard/card-visibility-control';
import { OverviewMetric } from '@/types/api';
import { Moon, Star } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SleepCardProps {
  metrics: OverviewMetric[];
  hiddenCards?: Set<string>;
  onToggleCard?: (cardId: string, hidden: boolean) => void;
  className?: string;
}

interface CircularProgressProps {
  value: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
}

function CircularProgress({
  value,
  size = 120,
  strokeWidth = 8,
  className = '',
}: CircularProgressProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (value / 100) * circumference;

  // Color based on score
  const getColor = (score: number) => {
    if (score >= 80) return '#22c55e'; // green
    if (score >= 60) return '#eab308'; // yellow
    if (score >= 40) return '#f97316'; // orange
    return '#ef4444'; // red
  };

  return (
    <div className={cn('relative', className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          className="text-muted"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={getColor(value)}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center flex-col">
        <span className="text-3xl font-bold">{value}</span>
        <span className="text-xs text-muted-foreground">睡眠评分</span>
      </div>
    </div>
  );
}

interface SleepStageBarProps {
  lightSleep: number | null;
  deepSleep: number | null;
  remSleep: number | null;
  total?: number | null;
}

function SleepStageBar({ lightSleep, deepSleep, remSleep, total }: SleepStageBarProps) {
  const lightSleepVal = lightSleep ?? 0;
  const deepSleepVal = deepSleep ?? 0;
  const remSleepVal = remSleep ?? 0;
  const totalHours = total ?? lightSleepVal + deepSleepVal + remSleepVal;

  if (totalHours === 0 || !isFinite(totalHours)) {
    return (
      <div className="text-center text-muted-foreground text-sm py-4">
        暂无睡眠阶段数据
      </div>
    );
  }

  const lightPercent = (lightSleepVal / totalHours) * 100;
  const deepPercent = (deepSleepVal / totalHours) * 100;
  const remPercent = (remSleepVal / totalHours) * 100;

  return (
    <div className="space-y-3">
      {/* Stacked bar */}
      <div className="h-4 rounded-full overflow-hidden flex">
        <div
          className="bg-sky-300 transition-all duration-300"
          style={{ width: `${lightPercent}%` }}
          title={`浅睡: ${lightSleepVal.toFixed(1)}h`}
        />
        <div
          className="bg-indigo-500 transition-all duration-300"
          style={{ width: `${deepPercent}%` }}
          title={`深睡: ${deepSleepVal.toFixed(1)}h`}
        />
        <div
          className="bg-purple-400 transition-all duration-300"
          style={{ width: `${remPercent}%` }}
          title={`REM: ${remSleepVal.toFixed(1)}h`}
        />
      </div>

      {/* Legend */}
      <div className="flex justify-around text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-sky-300" />
          <span>浅睡 {lightSleepVal.toFixed(1)}h</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-indigo-500" />
          <span>深睡 {deepSleepVal.toFixed(1)}h</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-purple-400" />
          <span>REM {remSleepVal.toFixed(1)}h</span>
        </div>
      </div>
    </div>
  );
}

export function SleepCard({
  metrics,
  hiddenCards = new Set(),
  onToggleCard,
  className = '',
}: SleepCardProps) {
  const isHidden = hiddenCards.has('sleep');

  if (isHidden) {
    return (
      <Card className={cn('opacity-50', className)}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">睡眠卡片已隐藏</span>
            {onToggleCard && (
              <CardVisibilityControl
                cardId="sleep"
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

  const avgSleepHours = calculateAverage((m) => m.sleep_hours ?? null);
  const avgLightSleep = calculateAverage((m) => m.light_sleep_hours ?? 0);
  const avgDeepSleep = calculateAverage((m) => m.deep_sleep_hours ?? 0);
  const avgRemSleep = calculateAverage((m) => m.rem_sleep_hours ?? 0);

  // Use Garmin's sleep score if available, otherwise calculate locally
  const calculateSleepScore = () => {
    // Try to use Garmin's sleep score (average across all users)
    const avgSleepScore = calculateAverage((m) => m.sleep_score ?? null);
    if (avgSleepScore !== null && avgSleepScore > 0) {
      return Math.round(avgSleepScore);
    }

    // Fallback: Calculate locally if Garmin score not available
    if (!avgSleepHours) return 0;

    let score = 0;

    // Total sleep score (ideal 7-9 hours)
    if (avgSleepHours >= 7 && avgSleepHours <= 9) {
      score += 40;
    } else if (avgSleepHours >= 6 && avgSleepHours < 7) {
      score += 30;
    } else if (avgSleepHours >= 9 && avgSleepHours <= 10) {
      score += 30;
    } else if (avgSleepHours > 0) {
      score += 10;
    }

    // Deep sleep score (ideal 1.5-2 hours)
    const deepSleepRatio = avgDeepSleep ? avgDeepSleep / avgSleepHours : 0;
    if (deepSleepRatio >= 0.15 && deepSleepRatio <= 0.25) {
      score += 30;
    } else if (deepSleepRatio >= 0.1 && deepSleepRatio < 0.15) {
      score += 20;
    } else if (deepSleepRatio > 0.25) {
      score += 15;
    } else if (deepSleepRatio > 0) {
      score += 10;
    }

    // REM sleep score (ideal 1.5-2.5 hours)
    const remSleepRatio = avgRemSleep ? avgRemSleep / avgSleepHours : 0;
    if (remSleepRatio >= 0.2 && remSleepRatio <= 0.3) {
      score += 30;
    } else if (remSleepRatio >= 0.15 && remSleepRatio < 0.2) {
      score += 20;
    } else if (remSleepRatio > 0.3) {
      score += 15;
    } else if (remSleepRatio > 0) {
      score += 10;
    }

    return Math.min(Math.round(score), 100);
  };

  const sleepScore = calculateSleepScore();

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Moon className="h-5 w-5 text-indigo-500" />
            <CardTitle>睡眠分析</CardTitle>
          </div>
          {onToggleCard && (
            <CardVisibilityControl
              cardId="sleep"
              isHidden={false}
              onToggle={onToggleCard}
            />
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left: Sleep Score and Total Hours */}
          <div className="flex flex-col items-center justify-center space-y-4">
            <CircularProgress value={sleepScore} />

            <div className="text-center">
              <div className="flex items-center justify-center gap-2">
                <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                <span className="text-2xl font-bold">
                  {avgSleepHours ? `${avgSleepHours.toFixed(1)}h` : 'N/A'}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">昨晚总睡眠时长</p>
            </div>

            {/* Sleep quality indicator */}
            <div className="text-center">
              <span
                className={cn(
                  'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium',
                  sleepScore >= 80
                    ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                    : sleepScore >= 60
                      ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
                      : sleepScore >= 40
                        ? 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300'
                        : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                )}
              >
                {sleepScore >= 80 ? '优质睡眠' : sleepScore >= 60 ? '良好睡眠' : sleepScore >= 40 ? '一般' : '需要改善'}
              </span>
            </div>
          </div>

          {/* Right: Sleep Stages */}
          <div className="flex flex-col justify-center">
            <h3 className="text-sm font-medium mb-4">睡眠阶段分布</h3>
            <SleepStageBar
              lightSleep={avgLightSleep}
              deepSleep={avgDeepSleep}
              remSleep={avgRemSleep}
              total={avgSleepHours ?? undefined}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
