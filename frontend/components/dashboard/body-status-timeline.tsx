// ABOUTME: Time-series chart for body status data (body battery, stress level)
// ABOUTME: Displays minute-level readings throughout the day using Recharts
'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { format } from 'date-fns';
import { Battery, Activity, Loader2 } from 'lucide-react';
import { getBodyStatusTimeseries } from '@/lib/api';
import { BodyStatusTimeseriesPoint } from '@/types/api';
import { cn } from '@/lib/utils';

interface BodyStatusTimelineProps {
  userId: number;
  date: string;
  className?: string;
}

interface ChartDataPoint {
  time: string;
  timestamp: Date;
  body_battery: number | null;
  stress_level: number | null;
}

export function BodyStatusTimeline({ userId, date, className }: BodyStatusTimelineProps) {
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const response = await getBodyStatusTimeseries(userId, date);
        const chartData = response.data.map((point: BodyStatusTimeseriesPoint) => ({
          time: format(new Date(point.timestamp), 'HH:mm'),
          timestamp: new Date(point.timestamp),
          body_battery: point.body_battery,
          stress_level: point.stress_level,
        }));
        setData(chartData);
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载失败');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [userId, date]);

  // Calculate stats
  const stats = {
    maxBattery: Math.max(...data.map(d => d.body_battery ?? 0)),
    minBattery: Math.min(...data.filter(d => d.body_battery !== null).map(d => d.body_battery!)),
    avgStress: data.filter(d => d.stress_level !== null).length > 0
      ? Math.round(data.filter(d => d.stress_level !== null)
          .reduce((sum, d) => sum + d.stress_level!, 0) / data.filter(d => d.stress_level !== null).length)
      : null,
  };

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            身体状态时间线
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-48">
          <p className="text-muted-foreground">暂无时间序列数据</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          身体状态时间线
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stats summary */}
        <div className="grid grid-cols-3 gap-2 text-sm">
          <StatBox
            label="最高电量"
            value={stats.maxBattery}
            unit="%"
            icon={Battery}
            color="text-green-500"
          />
          <StatBox
            label="最低电量"
            value={stats.minBattery}
            unit="%"
            icon={Battery}
            color="text-orange-500"
          />
          <StatBox
            label="平均压力"
            value={stats.avgStress}
            unit=""
            icon={Activity}
            color="text-blue-500"
          />
        </div>

        {/* Chart */}
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10 }}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 10 }}
              width={30}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #e5e7eb',
                borderRadius: '6px',
                fontSize: '12px',
              }}
              formatter={(value: number, name: string) => [
                `${value}${name === '身体电量' ? '%' : ''}`,
                name
              ]}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Line
              type="monotone"
              dataKey="body_battery"
              stroke="#22c55e"
              strokeWidth={2}
              name="身体电量"
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="stress_level"
              stroke="#f59e0b"
              strokeWidth={2}
              name="压力值"
              dot={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

interface StatBoxProps {
  label: string;
  value: number | null;
  unit: string;
  icon: React.ElementType;
  color: string;
}

function StatBox({ label, value, unit, icon: Icon, color }: StatBoxProps) {
  return (
    <div className="flex items-center gap-2 p-2 bg-muted/30 rounded-lg">
      <Icon className={cn('h-4 w-4', color)} />
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="font-semibold">
          {value !== null ? `${value}${unit}` : 'N/A'}
        </p>
      </div>
    </div>
  );
}
