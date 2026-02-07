/**
 * Trend Chart Component
 * Displays sleep vs work load correlation using dual Y-axis line chart
 */
'use client';

import { DailyTrendData } from '@/types/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
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

interface TrendChartProps {
  data: DailyTrendData[];
  startDate: string;
  endDate: string;
}

export function TrendChart({ data, startDate, endDate }: TrendChartProps) {
  // Group data by date and aggregate across users
  const aggregatedData = data.reduce((acc, item) => {
    const dateKey = item.date;
    if (!acc[dateKey]) {
      acc[dateKey] = {
        date: dateKey,
        totalSleep: 0,
        totalWork: 0,
        sleepCount: 0,
        workCount: 0,
      };
    }

    if (item.sleep_hours !== null) {
      acc[dateKey].totalSleep += item.sleep_hours;
      acc[dateKey].sleepCount += 1;
    }

    if (item.total_work_minutes !== null) {
      acc[dateKey].totalWork += item.total_work_minutes / 60; // Convert to hours
      acc[dateKey].workCount += 1;
    }

    return acc;
  }, {} as Record<string, any>);

  // Calculate averages and format for chart
  const chartData = Object.values(aggregatedData).map((item: any) => ({
    date: format(new Date(item.date), 'MM/dd'),
    sleep: item.sleepCount > 0 ? (item.totalSleep / item.sleepCount).toFixed(1) : null,
    work: item.workCount > 0 ? (item.totalWork / item.workCount).toFixed(1) : null,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sleep vs Work Load Trends</CardTitle>
        <CardDescription>
          Analyzing correlation between work hours and sleep quality
          ({format(new Date(startDate), 'MMM dd')} - {format(new Date(endDate), 'MMM dd')})
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              label={{ value: 'Date', position: 'insideBottom', offset: -5 }}
            />
            <YAxis
              yAxisId="left"
              label={{ value: 'Work Hours', angle: -90, position: 'insideLeft' }}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              label={{ value: 'Sleep Hours', angle: 90, position: 'insideRight' }}
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #ccc',
                borderRadius: '4px',
              }}
            />
            <Legend />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="work"
              stroke="#f97316"
              strokeWidth={2}
              name="Work Hours"
              dot={{ r: 4 }}
              connectNulls
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="sleep"
              stroke="#3b82f6"
              strokeWidth={2}
              name="Sleep Hours"
              dot={{ r: 4 }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
