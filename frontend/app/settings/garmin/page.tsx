'use client';

import { ProtectedRoute } from '@/components/protected-route';
import { SiteHeader } from '@/components/site-header';
import { GarminConnectionCard } from '@/components/garmin-connection-card';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function GarminSettingsPage() {
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
              <h1 className="text-3xl font-bold">Garmin Connect</h1>
              <p className="text-muted-foreground">
                Sync your health data from Garmin Connect automatically
              </p>
            </div>
          </div>

          <div className="space-y-6">
            <GarminConnectionCard onSyncComplete={handleSyncComplete} />

            {/* Information Card */}
            <div className="rounded-lg border p-6 space-y-4">
              <h2 className="text-lg font-semibold">About Garmin Connect Integration</h2>
              <p className="text-sm text-muted-foreground">
                Connect your Garmin account to automatically sync the following health metrics:
              </p>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <span className="text-green-500 mt-0.5">●</span>
                  <span><strong>Sleep Hours</strong> - Total sleep duration per day</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-500 mt-0.5">●</span>
                  <span><strong>Resting Heart Rate</strong> - Your resting BPM</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-500 mt-0.5">●</span>
                  <span><strong>Stress Level</strong> - Daily stress score (0-100)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-500 mt-0.5">●</span>
                  <span><strong>Exercise Minutes</strong> - Total active time</span>
                </li>
              </ul>

              <div className="pt-4 border-t">
                <h3 className="font-medium mb-2">How it works</h3>
                <ol className="space-y-2 text-sm text-muted-foreground list-decimal list-inside">
                  <li>Click "Link Garmin Account" and enter your Garmin credentials</li>
                  <li>If you have 2FA enabled, provide your MFA token</li>
                  <li>Your credentials are encrypted and stored securely</li>
                  <li>Data syncs automatically when you click "Sync Now"</li>
                </ol>
              </div>

              <div className="pt-4 border-t">
                <h3 className="font-medium mb-2">Privacy & Security</h3>
                <p className="text-sm text-muted-foreground">
                  Your Garmin username and password are encrypted before saving to the database
                  using AES encryption. We use the community garminconnect library to access
                  Garmin data. You can unlink your account at any time to stop data
                  synchronization and delete your stored credentials.
                </p>
              </div>
            </div>

            {/* Developer Info */}
            <div className="rounded-lg bg-muted p-4">
              <h3 className="font-medium mb-2 text-sm">For Developers</h3>
              <p className="text-xs text-muted-foreground mb-2">
                This integration uses the community <code className="bg-background px-1 py-0.5 rounded">python-garminconnect</code> library
                which uses username/password authentication. No API keys or OAuth setup required.
              </p>
              <p className="text-xs text-muted-foreground">
                Note: This is an unofficial library that reverse-engineers Garmin's private API.
                Garmin may change their API at any time, which could break the integration.
              </p>
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
