import { ProtectedRoute } from '@/components/protected-route';
import { SiteHeader } from '@/components/site-header';
import Link from 'next/link';

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background">
        <SiteHeader />

        <main className="container mx-auto px-4 py-8 max-w-4xl">
          <h1 className="text-3xl font-bold mb-8">Settings</h1>

          <div className="grid gap-6 md:grid-cols-2">
            {/* Integrations */}
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">Integrations</h2>

              <Link
                href="/settings/garmin"
                className="block p-4 rounded-lg border hover:bg-accent transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                    <svg
                      className="h-6 w-6 text-blue-600 dark:text-blue-400"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-medium">Garmin Connect</h3>
                    <p className="text-sm text-muted-foreground">
                      Sync health data from your Garmin device
                    </p>
                  </div>
                </div>
              </Link>
            </div>

            {/* Notifications */}
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">Notifications</h2>

              <Link
                href="/settings/email"
                className="block p-4 rounded-lg border hover:bg-accent transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-orange-100 dark:bg-orange-900 flex items-center justify-center">
                    <svg
                      className="h-5 w-5 text-orange-600 dark:text-orange-400"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <rect width="20" height="16" x="2" y="4" rx="2" />
                      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-medium">Email Settings</h3>
                    <p className="text-sm text-muted-foreground">
                      Configure SMTP and notification recipients
                    </p>
                  </div>
                </div>
              </Link>
            </div>

            {/* Account Settings */}
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">Account</h2>

              <Link
                href="/settings/profile"
                className="block p-4 rounded-lg border hover:bg-accent transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                    <svg
                      className="h-5 w-5 text-purple-600 dark:text-purple-400"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-medium">Profile</h3>
                    <p className="text-sm text-muted-foreground">
                      Manage your profile information
                    </p>
                  </div>
                </div>
              </Link>

              <Link
                href="/settings/security"
                className="block p-4 rounded-lg border hover:bg-accent transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
                    <svg
                      className="h-5 w-5 text-green-600 dark:text-green-400"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-medium">Security</h3>
                    <p className="text-sm text-muted-foreground">
                      Change password and security settings
                    </p>
                  </div>
                </div>
              </Link>
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
