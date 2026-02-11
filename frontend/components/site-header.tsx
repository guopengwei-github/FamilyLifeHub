'use client';

import Link from 'next/link';
import { useAuth } from '@/contexts/auth-context';
import { LogOut, User as UserIcon, Activity, Settings } from 'lucide-react';
import { UserSelectDropdown } from '@/components/dashboard/user-select-dropdown';
import { SwitchToMeButton } from '@/components/dashboard/switch-to-me-button';
import { User } from '@/types/api';

interface SiteHeaderProps {
  users?: User[];
  viewingUser?: User | null;
  onViewingUserChange?: (user: User) => void;
  showUserSwitcher?: boolean;
}

export function SiteHeader({
  users = [],
  viewingUser = null,
  onViewingUserChange,
  showUserSwitcher = false,
}: SiteHeaderProps) {
  const { user, logout } = useAuth();

  return (
    <header className="border-b">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          {/* Logo and navigation */}
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2">
              <Activity className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">FamilyLifeHub</span>
            </Link>
            <nav className="flex items-center gap-4">
              <Link
                href="/"
                className="text-sm font-medium hover:text-primary transition-colors"
              >
                Dashboard
              </Link>
              <Link
                href="/health"
                className="text-sm font-medium hover:text-primary transition-colors"
              >
                Health Data
              </Link>
              <Link
                href="/settings"
                className="text-sm font-medium hover:text-primary transition-colors"
              >
                Settings
              </Link>
            </nav>
          </div>

          {/* Center: User Switcher (only on dashboard) */}
          {showUserSwitcher && user && users.length > 0 && (
            <div className="flex items-center gap-2 hidden md:flex">
              <span className="text-sm text-muted-foreground hidden sm:inline-block">查看:</span>
              <UserSelectDropdown
                users={users}
                viewingUser={viewingUser}
                currentUser={user}
                onChange={onViewingUserChange || (() => {})}
              />
              <SwitchToMeButton
                viewingUser={viewingUser}
                currentUser={user}
                onClick={() => onViewingUserChange?.(user)}
              />
            </div>
          )}

          {/* User menu */}
          {user && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                {user.avatar ? (
                  <img
                    src={user.avatar}
                    alt={user.name}
                    className="h-8 w-8 rounded-full object-cover"
                  />
                ) : (
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <UserIcon className="h-4 w-4 text-primary" />
                  </div>
                )}
                <span className="text-sm font-medium hidden sm:inline-block">
                  {user.name}
                </span>
              </div>
              <button
                onClick={logout}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline-block">Logout</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
