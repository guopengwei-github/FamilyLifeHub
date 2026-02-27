'use client';

import { Card, CardContent } from '@/components/ui/card';
import { SummaryResponse, User } from '@/types/api';
import { Moon, Footprints, Flame, Clock, Heart, Eye, RefreshCw, Link2 } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { getAvatarUrl } from '@/lib/api';
import { useRouter } from 'next/navigation';

type GarminSyncStatus = 'not_connected' | 'fresh' | 'stale' | 'severely_stale' | 'syncing' | 'error';

interface GarminSyncState {
  status: GarminSyncStatus;
  hoursAgo?: number;
  lastSyncAt?: Date | null;
}

interface UserSummaryCardProps {
  summary: SummaryResponse;
  currentUser: User | null;
  viewingUser: User | null;
  garminSyncState?: GarminSyncState;
  onGarminSync?: () => void;
}

export function UserSummaryCard({ summary, currentUser, viewingUser, garminSyncState, onGarminSync }: UserSummaryCardProps) {
  const router = useRouter();
  const { user_name, avatar, metrics } = summary;

  const isViewingSelf = viewingUser?.id === currentUser?.id;

  const getInitials = (name: string) => {
    return name.charAt(0).toUpperCase();
  };

  // Get Garmin sync status display
  const getGarminSyncDisplay = () => {
    if (!garminSyncState) return null;

    const { status, hoursAgo } = garminSyncState;

    const handleClick = () => {
      if (status === 'not_connected') {
        router.push('/settings?tab=garmin');
      } else if (onGarminSync && status !== 'syncing') {
        onGarminSync();
      }
    };

    let text: string;
    let className: string;
    let clickable = true;

    switch (status) {
      case 'not_connected':
        text = '未连接设备';
        className = 'text-muted-foreground cursor-pointer hover:text-foreground';
        break;
      case 'fresh':
        if (hoursAgo !== undefined && hoursAgo < 1) {
          text = '上次从 Garmin 获取数据：刚刚';
        } else {
          const hours = Math.floor(hoursAgo || 0);
          text = `上次从 Garmin 获取数据：${hours}小时前`;
        }
        className = 'text-green-600 cursor-pointer hover:text-green-700';
        break;
      case 'stale':
        text = '数据已过期，请同步设备。检查你的设备是否已同步到 Garmin app';
        className = 'text-yellow-600 cursor-pointer hover:text-yellow-700';
        break;
      case 'severely_stale':
        text = '数据严重过期，请同步设备。检查你的设备是否已同步到 Garmin app';
        className = 'text-red-600 cursor-pointer hover:text-red-700';
        break;
      case 'syncing':
        text = '同步中...';
        className = 'text-muted-foreground cursor-not-allowed';
        clickable = false;
        break;
      case 'error':
        text = '同步失败，点击重试';
        className = 'text-red-600 cursor-pointer hover:text-red-700';
        break;
      default:
        return null;
    }

    return (
      <div
        onClick={clickable ? handleClick : undefined}
        className={`flex items-center gap-1 text-sm ${className} ${!clickable ? '' : 'underline decoration-dotted'}`}
      >
        {status === 'syncing' && <RefreshCw className="h-3 w-3 animate-spin" />}
        {status === 'not_connected' && <Link2 className="h-3 w-3" />}
        {status === 'error' && <RefreshCw className="h-3 w-3" />}
        <span>{text}</span>
      </div>
    );
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
              <AvatarImage src={getAvatarUrl(avatar)} />
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
              {isViewingSelf && getGarminSyncDisplay()}
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
