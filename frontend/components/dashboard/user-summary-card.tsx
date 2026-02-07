'use client';

import { Card, CardContent } from '@/components/ui/card';
import { SummaryResponse } from '@/types/api';
import { Moon, Footprints, Flame, Clock, Heart } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

interface UserSummaryCardProps {
  summary: SummaryResponse;
}

export function UserSummaryCard({ summary }: UserSummaryCardProps) {
  const { user_name, avatar, metrics } = summary;

  const summaryItems = [
    {
      icon: Moon,
      value: metrics.sleep_hours ? `${metrics.sleep_hours.toFixed(1)}h` : 'N/A',
      label: 'Sleep',
      color: 'text-blue-500',
    },
    {
      icon: Footprints,
      value: metrics.steps ? metrics.steps.toLocaleString() : 'N/A',
      label: 'Steps',
      color: 'text-green-500',
    },
    {
      icon: Flame,
      value: metrics.calories ? `${metrics.calories}` : 'N/A',
      label: 'Calories',
      color: 'text-orange-500',
    },
    {
      icon: Clock,
      value: metrics.work_hours ? `${metrics.work_hours.toFixed(1)}h` : 'N/A',
      label: 'Work',
      color: 'text-purple-500',
    },
    {
      icon: Heart,
      value: metrics.stress_level ? `${metrics.stress_level}` : 'N/A',
      label: 'Stress',
      color: 'text-red-500',
    },
  ];

  return (
    <Card className="border-2">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          {/* Left: User Info */}
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16">
              <AvatarImage src={avatar || undefined} />
              <AvatarFallback className="text-xl">
                {user_name.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div>
              <h2 className="text-2xl font-bold">{user_name}</h2>
              <p className="text-muted-foreground">
                {new Date(summary.date).toLocaleDateString('zh-CN', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  weekday: 'long'
                })}
              </p>
            </div>
          </div>

          {/* Right: Summary Metrics */}
          <div className="flex gap-8">
            {summaryItems.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label} className="text-center">
                  <Icon className={`h-6 w-6 mx-auto mb-1 ${item.color}`} />
                  <p className="text-2xl font-bold">{item.value}</p>
                  <p className="text-xs text-muted-foreground">{item.label}</p>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
