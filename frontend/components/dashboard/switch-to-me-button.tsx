'use client';

import { ArrowLeft } from 'lucide-react';
import { User } from '@/types/api';
import { cn } from '@/lib/utils';

interface SwitchToMeButtonProps {
  viewingUser: User | null;
  currentUser: User | null;
  onClick: () => void;
  className?: string;
}

export function SwitchToMeButton({
  viewingUser,
  currentUser,
  onClick,
  className = '',
}: SwitchToMeButtonProps) {
  // Don't show if viewing self or no users
  if (!viewingUser || !currentUser || viewingUser.id === currentUser.id) {
    return null;
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex items-center gap-1.5 px-3 py-1.5 text-sm',
        'rounded-md border hover:bg-muted transition-colors',
        'text-muted-foreground hover:text-foreground',
        className
      )}
    >
      <ArrowLeft className="h-4 w-4" />
      <span>切换到我自己</span>
    </button>
  );
}
