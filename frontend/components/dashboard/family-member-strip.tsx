'use client';

import { useState } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';
import { OverviewMetric, User } from '@/types/api';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';

interface FamilyMemberStripProps {
  members: User[];
  metrics: OverviewMetric[];
  currentUserId: number;
  onMemberClick?: (userId: number) => void;
  className?: string;
}

interface MemberMiniCardProps {
  user: User;
  metrics: OverviewMetric | undefined;
  onClick: () => void;
  isCurrentUser: boolean;
}

function MemberMiniCard({ user, metrics, onClick, isCurrentUser }: MemberMiniCardProps) {
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  // Get a quick status indicator
  const getStatusInfo = () => {
    if (!metrics) return { color: 'bg-gray-400', label: '无数据' };

    const stressLevel = metrics.stress_level ?? 50;
    if (stressLevel <= 25) return { color: 'bg-green-400', label: '平静' };
    if (stressLevel <= 50) return { color: 'bg-blue-400', label: '放松' };
    if (stressLevel <= 75) return { color: 'bg-orange-400', label: '压力' };
    return { color: 'bg-red-400', label: '高压力' };
  };

  const status = getStatusInfo();

  return (
    <button
      onClick={onClick}
      className={cn(
        'flex-shrink-0 w-32 flex flex-col items-center p-3 rounded-lg border-2 transition-all hover:scale-105',
        isCurrentUser
          ? 'border-primary bg-primary/5'
          : 'border-border hover:border-primary/50'
      )}
    >
      <div className="relative mb-2">
        <Avatar className="h-14 w-14">
          <AvatarImage src={user.avatar || undefined} />
          <AvatarFallback className="text-lg bg-primary/10">
            {getInitials(user.name)}
          </AvatarFallback>
        </Avatar>
        {/* Status indicator dot */}
        <div
          className={cn(
            'absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-2 border-background',
            status.color
          )}
        />
      </div>

      <p className="font-medium text-sm truncate w-full text-center">{user.name}</p>
      {metrics ? (
        <p className="text-xs text-muted-foreground text-center">
          {metrics.sleep_hours ? `${metrics.sleep_hours}h 睡眠` : '无睡眠数据'}
        </p>
      ) : (
        <p className="text-xs text-muted-foreground text-center">无今日数据</p>
      )}

      {isCurrentUser && (
        <span className="text-xs text-primary font-medium mt-1">当前用户</span>
      )}
    </button>
  );
}

export function FamilyMemberStrip({
  members,
  metrics,
  currentUserId,
  onMemberClick,
  className = '',
}: FamilyMemberStripProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Create a map of user_id to metrics
  const metricsByUserId = new Map(
    metrics.map((m) => [m.user_id, m])
  );

  // Filter out current user from the strip
  const otherMembers = members.filter((m) => m.id !== currentUserId);

  if (otherMembers.length === 0) {
    return null;
  }

  return (
    <div className={cn('space-y-3', className)}>
      {/* Header with expand/collapse button */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">家庭成员</h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-2 rounded-md hover:bg-muted transition-colors"
          aria-label={isExpanded ? '收起' : '展开'}
        >
          {isExpanded ? (
            <ChevronUp className="h-5 w-5" />
          ) : (
            <ChevronDown className="h-5 w-5" />
          )}
        </button>
      </div>

      {/* Scrollable member cards */}
      {isExpanded && (
        <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent">
          {otherMembers.map((member) => (
            <MemberMiniCard
              key={member.id}
              user={member}
              metrics={metricsByUserId.get(member.id)}
              onClick={() => onMemberClick?.(member.id)}
              isCurrentUser={false}
            />
          ))}
        </div>
      )}
    </div>
  );
}
