'use client';

import Link from 'next/link';
import { useAuth } from '@/contexts/auth-context';
import { LogOut, User as UserIcon, Activity, Settings } from 'lucide-react';

export function SiteHeader() {
  const { user, logout } = useAuth();

  return (
    <header className="border-b">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
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
