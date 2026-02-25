'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CardVisibilityControl } from '@/components/dashboard/card-visibility-control';
import { OverviewMetric } from '@/types/api';
import { Battery, Droplets, Wind, HeartPulse, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface BodyStatusCardProps {
  metrics: OverviewMetric[];
  hiddenCards?: Set<string>;
  onToggleCard?: (cardId: string, hidden: boolean) => void;
  className?: string;
}

interface RecoveryStatus {
  icon: string;
  label: string;
  suggestion: string;
  color: string;
}

function getRecoveryStatus(bodyBattery: number | null, stressLevel: number | null): RecoveryStatus {
  if (bodyBattery === null) {
    return { icon: '❓', label: '未知', suggestion: '暂无数据', color: 'text-muted-foreground' };
  }

  const stress = stressLevel ?? 50;

  if (bodyBattery >= 70 && stress <= 30) {
    return { icon: '✅', label: '恢复良好', suggestion: '适合高强度运动', color: 'text-green-500' };
  } else if (bodyBattery >= 50 && stress <= 50) {
    return { icon: '🟡', label: '恢复中', suggestion: '适合中等强度运动', color: 'text-yellow-500' };
  } else if (bodyBattery >= 30) {
    return { icon: '🟠', label: '需要休息', suggestion: '建议轻度活动', color: 'text-orange-500' };
  } else {
    return { icon: '🔴', label: '疲劳', suggestion: '建议充分休息', color: 'text-red-500' };
  }
}

export function BodyStatusCard({
  metrics,
  hiddenCards = new Set(),
  onToggleCard,
  className = '',
}: BodyStatusCardProps) {
  const isHidden = hiddenCards.has('body_status');

  if (isHidden) {
    return (
      <Card className={cn('opacity-50', className)}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">身体状态卡片已隐藏</span>
            {onToggleCard && (
              <CardVisibilityControl cardId="body_status" isHidden={true} onToggle={onToggleCard} />
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

  const healthMetrics = {
    bodyBattery: calculateAverage((m) => m.body_battery ?? null),
    spo2: calculateAverage((m) => m.spo2 ?? null),
    respirationRate: calculateAverage((m) => m.respiration_rate ?? null),
    restingHr: calculateAverage((m) => m.resting_hr ?? null),
    stressLevel: calculateAverage((m) => m.stress_level ?? null),
  };

  const recovery = getRecoveryStatus(healthMetrics.bodyBattery, healthMetrics.stressLevel);
  const batteryPercent = healthMetrics.bodyBattery ?? 0;

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-500" />
            身体状态
          </CardTitle>
          {onToggleCard && (
            <CardVisibilityControl cardId="body_status" isHidden={false} onToggle={onToggleCard} />
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 身体电量和恢复状态 */}
        <div className="grid grid-cols-2 gap-4">
          {/* 身体电量 */}
          <div className="flex flex-col items-center p-4 bg-muted/50 rounded-lg">
            <Battery className="h-8 w-8 text-green-500 mb-2" />
            <span className="text-3xl font-bold">
              {healthMetrics.bodyBattery !== null ? `${healthMetrics.bodyBattery}%` : 'N/A'}
            </span>
            <span className="text-sm text-muted-foreground">身体电量</span>
            {/* 电量条 */}
            <div className="w-full h-2 bg-muted rounded-full mt-2 overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all',
                  batteryPercent >= 70 ? 'bg-green-500' :
                  batteryPercent >= 40 ? 'bg-yellow-500' :
                  batteryPercent >= 20 ? 'bg-orange-500' : 'bg-red-500'
                )}
                style={{ width: `${batteryPercent}%` }}
              />
            </div>
          </div>

          {/* 恢复状态 */}
          <div className="flex flex-col items-center justify-center p-4 bg-muted/50 rounded-lg">
            <span className="text-3xl mb-2">{recovery.icon}</span>
            <span className={cn('font-semibold', recovery.color)}>{recovery.label}</span>
            <span className="text-xs text-muted-foreground text-center mt-1">
              {recovery.suggestion}
            </span>
          </div>
        </div>

        {/* 生理指标 */}
        <div className="grid grid-cols-3 gap-3">
          <MetricBox
            icon={Droplets}
            value={healthMetrics.spo2}
            unit="%"
            label="血氧"
            color="text-blue-500"
          />
          <MetricBox
            icon={Wind}
            value={healthMetrics.respirationRate}
            unit="/分"
            label="呼吸"
            color="text-cyan-500"
          />
          <MetricBox
            icon={HeartPulse}
            value={healthMetrics.restingHr}
            unit="bpm"
            label="心率"
            color="text-red-500"
          />
        </div>
      </CardContent>
    </Card>
  );
}

interface MetricBoxProps {
  icon: React.ElementType;
  value: number | null;
  unit: string;
  label: string;
  color: string;
}

function MetricBox({ icon: Icon, value, unit, label, color }: MetricBoxProps) {
  return (
    <div className="flex flex-col items-center p-3 bg-muted/30 rounded-lg">
      <Icon className={cn('h-5 w-5 mb-1', color)} />
      <span className="text-lg font-semibold">
        {value !== null ? `${value}${unit}` : 'N/A'}
      </span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}
