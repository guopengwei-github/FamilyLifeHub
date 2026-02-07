'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  getStravaConnection,
  getStravaConfig,
  saveStravaConfig,
  unlinkStrava,
  syncStrava,
  getStravaAuthUrl,
  stravaCallback,
} from '@/lib/api';
import { StravaConnection } from '@/types/api';
import { Loader2, Unlink, RefreshCw, CheckCircle, AlertCircle, ExternalLink, Bike, Mountain, MapPin, Key, Save } from 'lucide-react';

interface StravaConnectionCardProps {
  onSyncComplete?: () => void;
}

export function StravaConnectionCard({ onSyncComplete }: StravaConnectionCardProps) {
  const [connection, setConnection] = useState<StravaConnection | null>(null);
  const [hasConfig, setHasConfig] = useState(false);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [showConfigForm, setShowConfigForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');

  useEffect(() => {
    fetchConnectionStatus();

    // Check if returning from Strava OAuth callback
    const handleStravaCallback = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const state = urlParams.get('state');

      if (code) {
        // Remove code from URL to avoid re-processing
        window.history.replaceState({}, document.title, window.location.pathname);
        await handleCallback(code);
      }
    };

    handleStravaCallback();
  }, []);

  const fetchConnectionStatus = async () => {
    try {
      setLoading(true);
      const [connData, configData] = await Promise.all([
        getStravaConnection(),
        getStravaConfig(),
      ]);
      setConnection(connData);
      setHasConfig(configData.has_config);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch Strava connection:', err);
      setError('Failed to load Strava connection status');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientId.trim() || !clientSecret.trim()) {
      setError('Please enter both Client ID and Client Secret');
      return;
    }

    try {
      setError(null);
      setSavingConfig(true);
      await saveStravaConfig(clientId.trim(), clientSecret.trim());
      setHasConfig(true);
      setShowConfigForm(false);
      setSyncResult('Strava app credentials saved successfully');
      // Clear sensitive fields
      setClientId('');
      setClientSecret('');
    } catch (err: any) {
      console.error('Failed to save Strava config:', err);
      const errorMsg = err?.message || 'Failed to save Strava config';
      setError(`Failed to save: ${errorMsg}`);
    } finally {
      setSavingConfig(false);
    }
  };

  const handleConnect = async () => {
    try {
      setError(null);
      // Get authorization URL
      const redirectUri = `${window.location.origin}`;
      const { authorization_url } = await getStravaAuthUrl(redirectUri);

      // Redirect to Strava for authorization
      window.location.href = authorization_url;
    } catch (err: any) {
      console.error('Failed to get Strava auth URL:', err);
      const errorMsg = err?.message || 'Failed to connect Strava account';
      setError(`Failed to connect: ${errorMsg}`);
    }
  };

  const handleCallback = async (code: string) => {
    try {
      setLoading(true);
      const data = await stravaCallback(code);
      setConnection(data);
      setSyncResult('Strava account connected successfully!');
      // Trigger initial sync after connection
      await handleSync();
    } catch (err: any) {
      console.error('Failed to complete Strava connection:', err);
      const errorMsg = err?.message || 'Failed to complete Strava connection';
      setError(`Connection failed: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUnlink = async () => {
    if (!confirm('Are you sure you want to unlink your Strava account? This will stop automatic data sync.')) {
      return;
    }

    try {
      setError(null);
      await unlinkStrava();
      setConnection({
        connected: false,
        athlete_name: null,
        athlete_id: null,
        athlete_profile: null,
        created_at: null,
        last_sync_at: null,
        sync_status: 'not_connected',
      });
      setSyncResult('Strava account unlinked successfully');
    } catch (err) {
      console.error('Failed to unlink Strava account:', err);
      setError('Failed to unlink Strava account');
    }
  };

  const handleSync = async () => {
    try {
      setError(null);
      setSyncResult(null);
      setSyncing(true);
      const result = await syncStrava(30);
      setConnection((prev) => ({
        ...prev!,
        last_sync_at: result.last_sync_at || new Date().toISOString(),
      }));

      if (result.success) {
        setSyncResult(
          `Sync complete: ${result.activities_synced} activity/activities synced, ` +
          `${result.metrics_updated} health metric(s) updated`
        );
        onSyncComplete?.();
      } else {
        setError('Sync completed with errors. Check your data.');
      }
    } catch (err) {
      console.error('Failed to sync Strava data:', err);
      setError('Failed to sync Strava data. Please try again.');
    } finally {
      setSyncing(false);
    }
  };

  if (loading && !connection) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const isConnected = connection?.connected;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <StravaIcon connected={isConnected} />
              Strava
            </CardTitle>
            <CardDescription>
              {isConnected
                ? 'Sync your runs, rides, and other activities from Strava'
                : 'Connect your Strava account to sync activity data'}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 p-3 rounded-md">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        )}

        {syncResult && (
          <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 dark:bg-green-950 dark:text-green-400 p-3 rounded-md">
            <CheckCircle className="h-4 w-4" />
            <span>{syncResult}</span>
          </div>
        )}

        {isConnected ? (
          <div className="space-y-4">
            <div className="rounded-md border p-4 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Athlete</span>
                <span className="font-medium">
                  {connection.athlete_name || 'Unknown'}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Status</span>
                <StatusBadge status={connection.sync_status} />
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Last Sync</span>
                <span className="font-medium">
                  {connection.last_sync_at
                    ? new Date(connection.last_sync_at).toLocaleString()
                    : 'Never'}
                </span>
              </div>
              {connection.athlete_profile && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Profile</span>
                  <a
                    href={connection.athlete_profile}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-700 dark:text-blue-400 flex items-center gap-1"
                  >
                    <ExternalLink className="h-3 w-3" />
                    View on Strava
                  </a>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <Button
                onClick={handleSync}
                disabled={syncing}
                variant="default"
                className="flex-1"
              >
                {syncing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Syncing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Sync Now
                  </>
                )}
              </Button>
              <Button
                onClick={handleUnlink}
                disabled={syncing}
                variant="outline"
                className="text-destructive hover:text-destructive"
              >
                <Unlink className="h-4 w-4 mr-2" />
                Unlink
              </Button>
            </div>
          </div>
        ) : showConfigForm ? (
          <form onSubmit={handleSaveConfig} className="space-y-4">
            <div className="space-y-3">
              <div>
                <Label htmlFor="client-id">Client ID</Label>
                <Input
                  id="client-id"
                  type="text"
                  placeholder="123456"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  disabled={savingConfig}
                  required
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Your Strava application Client ID
                </p>
              </div>
              <div>
                <Label htmlFor="client-secret">Client Secret</Label>
                <Input
                  id="client-secret"
                  type="password"
                  placeholder="Your Strava Client Secret"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                  disabled={savingConfig}
                  required
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Your Strava application Client Secret (kept secure)
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                type="submit"
                disabled={savingConfig}
                className="flex-1"
              >
                {savingConfig ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save Credentials
                  </>
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setShowConfigForm(false);
                  setClientId('');
                  setClientSecret('');
                }}
              >
                Cancel
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            {hasConfig ? (
              <div className="rounded-md border p-4 bg-blue-50 dark:bg-blue-950/30">
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">App credentials configured</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Your Strava app credentials are saved. You can now connect your account.
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowConfigForm(true)}
                    className="text-xs"
                  >
                    <Key className="h-3 w-3 mr-1" />
                    Edit
                  </Button>
                </div>
              </div>
            ) : (
              <div className="rounded-md border p-4 bg-amber-50 dark:bg-amber-950/30">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">App credentials required</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Each family member needs to configure their own Strava app credentials.
                    </p>
                  </div>
                </div>
              </div>
            )}
            <Button
              onClick={handleConnect}
              disabled={loading || syncing || !hasConfig}
              className="w-full"
              variant="default"
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              Connect Strava Account
            </Button>
            {!hasConfig && (
              <Button
                onClick={() => setShowConfigForm(true)}
                disabled={loading || savingConfig}
                className="w-full"
                variant="outline"
              >
                <Key className="h-4 w-4 mr-2" />
                Configure App Credentials
              </Button>
            )}
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          Strava integration syncs your activities including runs, rides, swims, and more.
          Each family member can configure their own Strava app credentials.
          OAuth tokens are encrypted and stored securely.
        </p>

        <div className="pt-2 border-t space-y-2">
          <div className="flex items-start gap-2 text-xs text-muted-foreground">
            <MapPin className="h-3 w-3 mt-0.5 shrink-0" />
            <div>
              <p>First, create a Strava app at </p>
              <a
                href="https://www.strava.com/settings/api"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-700 dark:text-blue-400 underline"
              >
                strava.com/settings/api
              </a>
            </div>
          </div>
          <div className="flex items-start gap-2 text-xs text-muted-foreground">
            <ExternalLink className="h-3 w-3 mt-0.5 shrink-0" />
            <div>
              <p>Authorization Callback Domain: </p>
              <code className="bg-muted px-1 py-0.5 rounded text-xs">localhost</code>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StravaIcon({ connected }: { connected?: boolean }) {
  return (
    <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
      connected ? 'bg-orange-100 dark:bg-orange-900' : 'bg-muted'
    }`}>
      <svg
        className={`h-5 w-5 ${connected ? 'text-orange-600 dark:text-orange-400' : 'text-muted-foreground'}`}
        viewBox="0 0 24 24"
        fill="currentColor"
      >
        <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7 13.828h4.169" />
      </svg>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, { label: string; className: string }> = {
    connected: {
      label: 'Connected',
      className: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-400',
    },
    error: {
      label: 'Error',
      className: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-400',
    },
    expired: {
      label: 'Expired',
      className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-400',
    },
    not_connected: {
      label: 'Not Connected',
      className: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
    },
  };

  const variant = variants[status] || variants.not_connected;

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${variant.className}`}>
      {variant.label}
    </span>
  );
}
