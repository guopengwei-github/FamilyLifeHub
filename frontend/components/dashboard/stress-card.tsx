'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CardVisibilityControl } from '@/components/dashboard/card-visibility-control';
import { OverviewMetric } from '@/types/api';
import { Heart, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StressCardProps {
  metrics: OverviewMetric[];
  hiddenCards?: Set<string>;
  onToggleCard?: (cardId: string, hidden: boolean) => void;
  className?: string;
}

interface StressGradientBarProps {
  value: number; // 0-100
}

function StressGradientBar({ value }: StressGradientBarProps) {
  const clampedValue = Math.max(0, Math.min(100, value));
  const markerPosition = clampedValue;

  return (
    <div className="relative">
      {/* Gradient bar */}
      <div className="h-3 w-full rounded-full bg-gradient-to-r from-green-400 via-yellow-400 via-orange-400 to-red-500" />

      {/* Marker */}
      <div
        className="absolute top-1/2 -translate-y-1/2 w-1 h-5 bg-gray-800 dark:bg-gray-200 rounded-full transform -translate-x-1/2 transition-all duration-300"
        style={{ left: `${markerPosition}%` }}
      />

      {/* Labels */}
      <div className="flex justify-between mt-1 text-xs text-muted-foreground">
        <span>平静</span>
        <span>放松</span>
        <span>压力</span>
        <span>高压力</span>
      </div>
    </div>
  );
}

interface MiniTrendChartProps {
  data: number[];
  color?: string;
}

function MiniTrendChart({ data, color = '#8b5cf6' }: MiniTrendChartProps) {
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;

  const points = data
    .map((value, index) => {
      const x = (index / (data.length - 1)) * 100;
      const y = 100 - ((value - min) / range) * 80 - 10; // Keep some padding
      return `${x},${y}`;
    })
    .join(' ');

  // Area fill points
  const areaPoints = `0,100 ${points} 100,100`;

  return (
    <svg viewBox="0 0 100 100" className="w-full h-full">
      {/* Area fill */}
      <polygon
        points={areaPoints}
        fill={color}
        fillOpacity="0.2"
      />
      {/* Line */}
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Dots */}
      {data.map((value, index) => {
        const x = (index / (data.length - 1)) * 100;
        const y = 100 - ((value - min) / range) * 80 - 10;
        return (
          <circle
            key={index}
            cx={x}
            cy={y}
            r="2"
            fill={color}
          />
        );
      })}
    </svg>
  );
}

export function StressCard({
  metrics,
  hiddenCards = new Set(),
  onToggleCard,
  className = '',
}: StressCardProps) {
  const isHidden = hiddenCards.has('stress');

  if (isHidden) {
    return (
      <Card className={cn('opacity-50', className)}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">压力卡片已隐藏</span>
            {onToggleCard && (
              <CardVisibilityControl
                cardId="stress"
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

  const avgStressLevel = calculateAverage((m) => m.stress_level ?? null);

  // Determine stress status
  const getStressStatus = (level: number | null) => {
    if (level === null) return { label: 'N/A', color: 'bg-gray-500', textColor: 'text-gray-500' };
    if (level <= 25) return { label: '平静', color: 'bg-green-500', textColor: 'text-green-500' };
    if (level <= 50) return { label: '放松', color: 'bg-blue-500', textColor: 'text-blue-500' };
    if (level <= 75) return { label: '压力', color: 'bg-orange-500', textColor: 'text-orange-500' };
    return { label: '高压力', color: 'bg-red-500', textColor: 'text-red-500' };
  };

  const stressStatus = getStressStatus(avgStressLevel);

  // Generate simulated trend data (in a real app, this would come from historical data)
  const generateTrendData = () => {
    const baseValue = avgStressLevel ?? 50;
    return Array.from({ length: 7 }, (_, i) => {
      // Simulate some variation
      const variation = Math.sin(i * 0.8) * 15 + Math.random() * 10 - 5;
      return Math.max(0, Math.min(100, baseValue + variation));
    });
  };

  const trendData = generateTrendData();

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Heart className="h-5 w-5 text-red-500" />
            <CardTitle>压力水平</CardTitle>
          </div>
          {onToggleCard && (
            <CardVisibilityControl
              cardId="stress"
              isHidden={false}
              onToggle={onToggleCard}
            />
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left: Current Stress Level */}
          <div className="flex flex-col justify-center space-y-6">
            {/* Large stress value display */}
            <div className="flex items-center gap-6">
              <div className="relative">
                <svg width="120" height="120" className="transform -rotate-90">
                  <circle
                    cx="60"
                    cy="60"
                    r="50"
                    stroke="currentColor"
                    strokeWidth="10"
                    fill="none"
                    className="text-muted"
                  />
                  <circle
                    cx="60"
                    cy="60"
                    r="50"
                    stroke={stressStatus.color.replace('bg-', 'text-').replace('500', '600')}
                    strokeWidth="10"
                    fill="none"
                    strokeDasharray={2 * Math.PI * 50}
                    strokeDashoffset={2 * Math.PI * 50 * (1 - (avgStressLevel ?? 0) / 100)}
                    strokeLinecap="round"
                    className="transition-all duration-500"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center flex-col">
                  <span className="text-3xl font-bold">
                    {avgStressLevel !== null ? Math.round(avgStressLevel) : '-'}
                  </span>
                  <span className="text-xs text-muted-foreground">压力值</span>
                </div>
              </div>

              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className={cn('h-5 w-5', stressStatus.textColor)} />
                  <span className="text-lg font-medium">当前状态</span>
                </div>
                <span
                  className={cn(
                    'inline-flex items-center px-4 py-2 rounded-full text-lg font-semibold',
                    stressStatus.color.replace('bg-', 'bg-').replace('500', '100'),
                    stressStatus.textColor.replace('text-', 'text-').replace('500', '700'),
                    'dark:' + stressStatus.color.replace('bg-', 'bg-').replace('500', '900'),
                    'dark:' + stressStatus.textColor.replace('text-', 'text-').replace('500', '300')
                  )}
                >
                  {stressStatus.label}
                </span>
              </div>
            </div>

            {/* Stress gradient bar */}
            <div>
              <p className="text-sm text-muted-foreground mb-3">压力水平分布</p>
              <StressGradientBar value={avgStressLevel ?? 0} />
            </div>
          </div>

          {/* Right: Daily Trend */}
          <div className="flex flex-col justify-center space-y-4">
            <div>
              <h3 className="text-sm font-medium mb-2">7日趋势</h3>
              <p className="text-xs text-muted-foreground">最近一周压力变化</p>
            </div>

            {/* Mini trend chart */}
            <div className="h-32 w-full">
              <MiniTrendChart data={trendData} color={stressStatus.textColor.replace('text-', '#')} />
            </div>

            {/* Trend summary */}
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div
                  className={cn('w-3 h-3 rounded-full', stressStatus.color)}
                />
                <span>平均值: {Math.round(trendData.reduce((a, b) => a + b, 0) / trendData.length)}</span>
              </div>
              <div className="text-muted-foreground">
                {trendData[trendData.length - 1] > trendData[0] ? '上升' : '下降'} 趋势
              </div>
            </div>

            {/* Daily labels */}
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>周一</span>
              <span>周二</span>
              <span>周三</span>
              <span>周四</span>
              <span>周五</span>
              <span>周六</span>
              <span>周日</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
