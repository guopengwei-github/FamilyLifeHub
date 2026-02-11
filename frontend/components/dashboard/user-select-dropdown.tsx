'use client';

import { useState, useRef, useEffect } from 'react';
import { Check, ChevronDown } from 'lucide-react';
import { User } from '@/types/api';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';

interface UserSelectDropdownProps {
  users: User[];
  viewingUser: User | null;
  currentUser: User | null;
  onChange: (user: User) => void;
  disabled?: boolean;
  className?: string;
}

export function UserSelectDropdown({
  users,
  viewingUser,
  currentUser,
  onChange,
  disabled = false,
  className = '',
}: UserSelectDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const handleSelect = (user: User) => {
    onChange(user);
    setIsOpen(false);
  };

  if (users.length <= 1) {
    // Single user - show as simple badge, no dropdown
    return (
      <div className={cn('flex items-center gap-2 px-3 py-1.5 rounded-md bg-muted/50', className)}>
        <Avatar className="h-5 w-5">
          <AvatarImage src={currentUser?.avatar || undefined} />
          <AvatarFallback className="text-xs">
            {currentUser ? getInitials(currentUser.name) : '??'}
          </AvatarFallback>
        </Avatar>
        <span className="text-sm font-medium">{currentUser?.name || 'Loading...'}</span>
      </div>
    );
  }

  return (
    <div ref={dropdownRef} className={cn('relative', className)}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-md border',
          'hover:bg-muted transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <Avatar className="h-5 w-5">
          <AvatarImage src={viewingUser?.avatar || undefined} />
          <AvatarFallback className="text-xs">
            {viewingUser ? getInitials(viewingUser.name) : '??'}
          </AvatarFallback>
        </Avatar>
        <span className="text-sm font-medium">
          {viewingUser?.name || 'Select User'}
        </span>
        <ChevronDown className={cn(
          'h-4 w-4 text-muted-foreground transition-transform',
          isOpen && 'transform rotate-180'
        )} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 z-50 min-w-[200px] max-h-[300px] overflow-y-auto bg-background border rounded-md shadow-lg">
          <div className="p-1">
            {users.map((user) => {
              const isCurrentUser = user.id === currentUser?.id;
              const isSelected = user.id === viewingUser?.id;

              return (
                <button
                  key={user.id}
                  type="button"
                  onClick={() => handleSelect(user)}
                  className={cn(
                    'w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors',
                    'hover:bg-muted',
                    isSelected && 'bg-accent'
                  )}
                >
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user.avatar || undefined} />
                    <AvatarFallback className="text-sm bg-primary/10">
                      {getInitials(user.name)}
                    </AvatarFallback>
                  </Avatar>

                  <div className="flex-1 text-left">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{user.name}</span>
                      {isCurrentUser && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                          我
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground">{user.email}</span>
                  </div>

                  {isSelected && (
                    <Check className="h-4 w-4 text-primary" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
