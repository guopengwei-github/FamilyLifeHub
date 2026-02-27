// ABOUTME: Embeddable chart component for body status time-series data
// ABOUTME: Displays body battery and stress level throughout the day
'use client';

import { useEffect, useState } from 'react';
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
import { Loader2 } from 'lucide-react';
import { getBodyStatusTimeseries } from '@/lib/api';
import { BodyStatusTimeseriesPoint } from '@/types/api';

interface BodyStatusTimelineChartProps {
  userId: number;
  date: string;
}

interface ChartDataPoint {
  time: string;
  body_battery: number | null;
  stress_level: number | null;
}

export function BodyStatusTimelineChart({ userId, date }: BodyStatusTimelineChartProps) {
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 bg-muted/30 rounded-lg">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-48 bg-muted/30 rounded-lg">
        <p className="text-sm text-muted-foreground">{error}</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 bg-muted/30 rounded-lg">
        <p className="text-sm text-muted-foreground">暂无时间序列数据</p>
      </div>
    );
  }

  return (
    <div className="pt-2">
      <p className="text-sm text-muted-foreground mb-2">今日变化趋势</p>
      <ResponsiveContainer width="100%" height={180}>
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
    </div>
  );
}
