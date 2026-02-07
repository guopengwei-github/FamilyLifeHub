'use client';

import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { OverviewMetric, User } from '@/types/api';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { SleepCard } from './sleep-card';
import { WorkCard } from './work-card';
import { StressCard } from './stress-card';
import { ActivityHealthCard } from './activity-health-card';

interface MemberDetailPanelProps {
  user: User | null;
  metrics: OverviewMetric[];
  allMetrics: OverviewMetric[]; // For calculating averages/comparisons
  isOpen: boolean;
  onClose: () => void;
  className?: string;
}

export function MemberDetailPanel({
  user,
  metrics,
  allMetrics,
  isOpen,
  onClose,
  className = '',
}: MemberDetailPanelProps) {
  const [hiddenCards, setHiddenCards] = useState<Set<string>>(new Set());

  // Close on ESC key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  if (!isOpen || !user) return null;

  // Filter metrics for this specific user
  const userMetrics = metrics.filter((m) => m.user_id === user.id);

  const handleToggleCard = (cardId: string, hidden: boolean) => {
    setHiddenCards((prev) => {
      const next = new Set(prev);
      if (hidden) {
        next.add(cardId);
      } else {
        next.delete(cardId);
      }
      return next;
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal Content */}
      <div
        className={cn(
          'relative bg-background rounded-lg shadow-lg max-w-4xl w-full max-h-[90vh] overflow-auto',
          className
        )}
      >
        {/* Header */}
        <div className="sticky top-0 bg-background border-b p-6 flex items-center justify-between z-10">
          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center text-2xl font-bold">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 className="text-2xl font-bold">{user.name}</h2>
              <p className="text-muted-foreground">
                {user.email}
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="关闭"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Date selector or summary could go here */}
          <p className="text-sm text-muted-foreground">
            显示今日数据概览
          </p>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Sleep Card */}
            <SleepCard
              metrics={userMetrics}
              hiddenCards={hiddenCards}
              onToggleCard={handleToggleCard}
            />

            {/* Work Card */}
            <WorkCard
              metrics={userMetrics}
              hiddenCards={hiddenCards}
              onToggleCard={handleToggleCard}
            />

            {/* Stress Card */}
            <StressCard
              metrics={userMetrics}
              hiddenCards={hiddenCards}
              onToggleCard={handleToggleCard}
            />

            {/* Activity/Health Card */}
            <ActivityHealthCard
              metrics={userMetrics}
              hiddenCards={hiddenCards}
              onToggleCard={handleToggleCard}
            />
          </div>

          {/* Comparison with family average could go here */}
          {allMetrics.length > 1 && (
            <div className="mt-8 pt-6 border-t">
              <h3 className="text-lg font-semibold mb-4">家庭平均对比</h3>
              <p className="text-sm text-muted-foreground">
                此功能即将推出，将显示家庭成员数据的对比分析。
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-background border-t p-4 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            关闭
          </Button>
        </div>
      </div>
    </div>
  );
}
