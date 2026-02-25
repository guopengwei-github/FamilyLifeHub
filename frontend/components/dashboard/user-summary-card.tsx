'use client';

import { Card, CardContent } from '@/components/ui/card';
import { SummaryResponse, User } from '@/types/api';
import { Moon, Footprints, Flame, Clock, Heart, Eye } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

interface UserSummaryCardProps {
  summary: SummaryResponse;
  currentUser: User | null;
  viewingUser: User | null;
}

export function UserSummaryCard({ summary, currentUser, viewingUser }: UserSummaryCardProps) {
  const { user_name, avatar, metrics } = summary;

  const isViewingSelf = viewingUser?.id === currentUser?.id;

  const getInitials = (name: string) => {
    return name.charAt(0).toUpperCase();
  };

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
                {getInitials(user_name)}
              </AvatarFallback>
            </Avatar>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold">{user_name}</h2>
                {!isViewingSelf && (
                  <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                    <Eye className="h-3 w-3" />
                    正在查看
                  </span>
                )}
              </div>
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
