// ABOUTME: HRV (Heart Rate Variability) card component for dashboard
// ABOUTME: Displays last night HRV average, status, and 7-day trend chart
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CardVisibilityControl } from '@/components/dashboard/card-visibility-control';
import { OverviewMetric, DailyTrendData } from '@/types/api';
import { HeartPulse, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

interface HRVCardProps {
  metrics: OverviewMetric[];
  trends: DailyTrendData[];
  hiddenCards?: Set<string>;
  onToggleCard?: (cardId: string, hidden: boolean) => void;
  className?: string;
}

interface MiniTrendChartProps {
  data: number[];
  color?: string;
}

function MiniTrendChart({ data, color = '#10b981' }: MiniTrendChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        暂无数据
      </div>
    );
  }

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
    <svg viewBox="0 0 100 100" className="w-full h-full">
      <polygon
        points={areaPoints}
        fill={color}
        fillOpacity="0.2"
      />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
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

interface HRVStatusConfig {
  label: string;
  color: string;
  bgColor: string;
  textColor: string;
}

function getHRVStatus(status: string | null | undefined): HRVStatusConfig {
  switch (status?.toUpperCase()) {
    case 'BALANCED':
      return {
        label: '平衡',
        color: '#10b981',
        bgColor: 'bg-green-100 dark:bg-green-900',
        textColor: 'text-green-700 dark:text-green-300',
      };
    case 'UNBALANCED':
      return {
        label: '不平衡',
        color: '#eab308',
        bgColor: 'bg-yellow-100 dark:bg-yellow-900',
        textColor: 'text-yellow-700 dark:text-yellow-300',
      };
    case 'LOW':
      return {
        label: '偏低',
        color: '#f97316',
        bgColor: 'bg-orange-100 dark:bg-orange-900',
        textColor: 'text-orange-700 dark:text-orange-300',
      };
    case 'POOR':
      return {
        label: '过低',
        color: '#ef4444',
        bgColor: 'bg-red-100 dark:bg-red-900',
        textColor: 'text-red-700 dark:text-red-300',
      };
    default:
      return {
        label: '未知',
        color: '#6b7280',
        bgColor: 'bg-gray-100 dark:bg-gray-800',
        textColor: 'text-gray-700 dark:text-gray-300',
      };
  }
}

export function HRVCard({
  metrics,
  trends,
  hiddenCards = new Set(),
  onToggleCard,
  className = '',
}: HRVCardProps) {
  const isHidden = hiddenCards.has('hrv');

  if (isHidden) {
    return (
      <Card className={cn('opacity-50', className)}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">HRV 卡片已隐藏</span>
            {onToggleCard && (
              <CardVisibilityControl
                cardId="hrv"
                isHidden={true}
                onToggle={onToggleCard}
              />
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Calculate average HRV across all users
  const hrvValues = metrics
    .map((m) => m.hrv_last_night)
    .filter((v): v is number => v !== null && v !== undefined);

  const avgHRV = hrvValues.length > 0
    ? Math.round(hrvValues.reduce((a, b) => a + b, 0) / hrvValues.length)
    : null;

  // Get HRV status (use first non-null status)
  const hrvStatus = metrics.find((m) => m.hrv_status)?.hrv_status || null;
  const statusConfig = getHRVStatus(hrvStatus);

  // Get weekly average
  const weeklyAvgValues = metrics
    .map((m) => m.hrv_weekly_avg)
    .filter((v): v is number => v !== null && v !== undefined);
  const weeklyAvg = weeklyAvgValues.length > 0
    ? Math.round(weeklyAvgValues.reduce((a, b) => a + b, 0) / weeklyAvgValues.length)
    : null;

  // Extract HRV trend data (last 7 days)
  const hrvTrendData = trends
    .filter((t) => t.hrv_last_night !== null && t.hrv_last_night !== undefined)
    .map((t) => t.hrv_last_night as number)
    .slice(-7);

  // Calculate trend direction
  const getTrendDirection = () => {
    if (hrvTrendData.length < 2) return null;
    const first = hrvTrendData[0];
    const last = hrvTrendData[hrvTrendData.length - 1];
    const diff = last - first;
    if (diff > 3) return 'up';
    if (diff < -3) return 'down';
    return 'stable';
  };

  const trendDirection = getTrendDirection();

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <HeartPulse className="h-5 w-5 text-pink-500" />
            <CardTitle>HRV (心率变异率)</CardTitle>
          </div>
          {onToggleCard && (
            <CardVisibilityControl
              cardId="hrv"
              isHidden={false}
              onToggle={onToggleCard}
            />
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left: Current HRV Value */}
          <div className="flex flex-col justify-center space-y-6">
            {/* Large HRV value display */}
            <div className="flex items-center gap-6">
              <div className="flex flex-col items-center justify-center">
                <span className="text-5xl font-bold" style={{ color: statusConfig.color }}>
                  {avgHRV !== null ? avgHRV : '-'}
                </span>
                <span className="text-sm text-muted-foreground mt-1">ms</span>
              </div>

              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: statusConfig.color }}
                  />
                  <span className="text-lg font-medium">状态</span>
                </div>
                <span
                  className={cn(
                    'inline-flex items-center px-4 py-2 rounded-full text-lg font-semibold',
                    statusConfig.bgColor,
                    statusConfig.textColor
                  )}
                >
                  {statusConfig.label}
                </span>
              </div>
            </div>

            {/* Weekly average */}
            {weeklyAvg !== null && (
              <div className="text-sm text-muted-foreground">
                周平均: <span className="font-medium text-foreground">{weeklyAvg} ms</span>
              </div>
            )}
          </div>

          {/* Right: 7-Day Trend */}
          <div className="flex flex-col justify-center space-y-4">
            <div>
              <h3 className="text-sm font-medium mb-2">7日趋势</h3>
              <p className="text-xs text-muted-foreground">最近一周 HRV 变化</p>
            </div>

            {/* Mini trend chart */}
            <div className="h-32 w-full">
              <MiniTrendChart data={hrvTrendData} color={statusConfig.color} />
            </div>

            {/* Trend summary */}
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: statusConfig.color }}
                />
                <span>
                  平均值:{' '}
                  {hrvTrendData.length > 0
                    ? Math.round(hrvTrendData.reduce((a, b) => a + b, 0) / hrvTrendData.length)
                    : '-'}
                </span>
              </div>
              <div className="flex items-center gap-1 text-muted-foreground">
                {trendDirection === 'up' && (
                  <>
                    <TrendingUp className="h-4 w-4 text-green-500" />
                    <span className="text-green-500">上升</span>
                  </>
                )}
                {trendDirection === 'down' && (
                  <>
                    <TrendingDown className="h-4 w-4 text-red-500" />
                    <span className="text-red-500">下降</span>
                  </>
                )}
                {trendDirection === 'stable' && (
                  <>
                    <Minus className="h-4 w-4" />
                    <span>稳定</span>
                  </>
                )}
                {trendDirection === null && <span>暂无趋势</span>}
              </div>
            </div>

            {/* Day labels */}
            {hrvTrendData.length > 0 && (
              <div className="flex justify-between text-xs text-muted-foreground">
                {hrvTrendData.map((_, index) => {
                  const dayOffset = hrvTrendData.length - 1 - index;
                  const date = new Date();
                  date.setDate(date.getDate() - dayOffset);
                  return (
                    <span key={index}>
                      {date.toLocaleDateString('zh-CN', { weekday: 'short' })}
                    </span>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
