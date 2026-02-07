'use client';

import { ProtectedRoute } from '@/components/protected-route';
import { SiteHeader } from '@/components/site-header';
import { StravaConnectionCard } from '@/components/strava-connection-card';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function StravaSettingsPage() {
  const router = useRouter();

  const handleSyncComplete = () => {
    // Refresh dashboard data after sync
    router.prefetch('/');
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background">
        <SiteHeader />

        <main className="container mx-auto px-4 py-8 max-w-4xl">
          {/* Back button */}
          <Link
            href="/settings"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Settings
          </Link>

          <div className="flex items-center gap-3 mb-8">
            <div className="h-10 w-10 rounded-full bg-orange-100 dark:bg-orange-900 flex items-center justify-center">
              <svg
                className="h-6 w-6 text-orange-600 dark:text-orange-400"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7 13.828h4.169" />
              </svg>
            </div>
            <div>
              <h1 className="text-3xl font-bold">Strava</h1>
              <p className="text-muted-foreground">
                Sync your runs, rides, and other activities from Strava
              </p>
            </div>
          </div>

          <div className="space-y-6">
            <StravaConnectionCard onSyncComplete={handleSyncComplete} />

            {/* Information Card */}
            <div className="rounded-lg border p-6 space-y-4">
              <h2 className="text-lg font-semibold">About Strava Integration</h2>
              <p className="text-sm text-muted-foreground">
                Connect your Strava account to automatically sync the following activity data:
              </p>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <span className="text-orange-500 mt-0.5">●</span>
                  <span><strong>Running</strong> - Track distance, pace, and time</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-orange-500 mt-0.5">●</span>
                  <span><strong>Cycling</strong> - Track rides and workouts</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-orange-500 mt-0.5">●</span>
                  <span><strong>Swimming</strong> - Pool and open water activities</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-orange-500 mt-0.5">●</span>
                  <span><strong>Other Activities</strong> - Hiking, skiing, and more</span>
                </li>
              </ul>

              <div className="pt-4 border-t">
                <h3 className="font-medium mb-2">How it works</h3>
                <ol className="space-y-2 text-sm text-muted-foreground list-decimal list-inside">
                  <li>Click "Connect Strava Account" to authorize the app</li>
                  <li>You will be redirected to Strava to grant permissions</li>
                  <li>After authorization, your activities will be synced</li>
                  <li>Click "Sync Now" to fetch recent activities manually</li>
                </ol>
              </div>

              <div className="pt-4 border-t">
                <h3 className="font-medium mb-2">Privacy & Security</h3>
                <p className="text-sm text-muted-foreground">
                  We use OAuth2 for secure authentication. Your Strava tokens are encrypted
                  before storing them in the database. You can unlink your account at any time
                  to stop data synchronization and delete your stored credentials.
                </p>
              </div>
            </div>

            {/* Developer Info */}
            <div className="rounded-lg bg-muted p-4">
              <h3 className="font-medium mb-2 text-sm">For Developers</h3>
              <p className="text-xs text-muted-foreground mb-2">
                This integration uses the official <code className="bg-background px-1 py-0.5 rounded">Strava API</code>
                with OAuth2 authentication.
              </p>
              <p className="text-xs text-muted-foreground mb-2">
                To enable this integration, create a Strava app at{' '}
                <a
                  href="https://www.strava.com/settings/api"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 underline"
                >
                  strava.com/settings/api
                </a>
                and configure the following environment variables in your backend:
              </p>
              <div className="space-y-1 text-xs font-mono bg-background p-2 rounded">
                <div>STRAVA_CLIENT_ID=your_client_id</div>
                <div>STRAVA_CLIENT_SECRET=your_client_secret</div>
                <div>STRAVA_REDIRECT_URI=http://localhost:8000/api/v1/strava/callback</div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
