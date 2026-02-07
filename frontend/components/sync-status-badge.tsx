'use client';

import { CheckCircle2, AlertTriangle, XCircle, Clock } from 'lucide-react';

interface SyncStatusBadgeProps {
  status: 'connected' | 'error' | 'expired' | 'not_connected';
  lastSyncAt?: string | null;
  showTime?: boolean;
}

export function SyncStatusBadge({ status, lastSyncAt, showTime }: SyncStatusBadgeProps) {
  const variants: Record<string, {
    icon: React.ReactNode;
    label: string;
    className: string;
  }> = {
    connected: {
      icon: <CheckCircle2 className="h-3 w-3" />,
      label: 'Synced',
      className: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-400 border-green-200 dark:border-green-800',
    },
    error: {
      icon: <AlertTriangle className="h-3 w-3" />,
      label: 'Error',
      className: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-400 border-red-200 dark:border-red-800',
    },
    expired: {
      icon: <XCircle className="h-3 w-3" />,
      label: 'Expired',
      className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800',
    },
    not_connected: {
      icon: <Clock className="h-3 w-3" />,
      label: 'Not Connected',
      className: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400 border-gray-200 dark:border-gray-700',
    },
  };

  const variant = variants[status] || variants.not_connected;

  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border">
      {variant.icon}
      <span>{variant.label}</span>
      {showTime && lastSyncAt && (
        <span className="text-muted-foreground">
          {formatLastSync(lastSyncAt)}
        </span>
      )}
    </div>
  );
}

function formatLastSync(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}
