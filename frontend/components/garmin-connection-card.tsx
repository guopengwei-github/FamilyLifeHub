'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  connectGarmin,
  getGarminConnection,
  unlinkGarmin,
  syncGarmin,
} from '@/lib/api';
import { GarminConnection } from '@/types/api';
import { Loader2, Unlink, RefreshCw, CheckCircle, AlertCircle, ExternalLink, Mail } from 'lucide-react';

interface GarminConnectionCardProps {
  onSyncComplete?: () => void;
}

// Step 1: Credentials
interface StepCredentialsProps {
  username: string;
  setUsername: (v: string) => void;
  password: string;
  setPassword: (v: string) => void;
  isCn: boolean;
  setIsCn: (v: boolean) => void;
  connecting: boolean;
  onNext: () => void;
  onCancel: () => void;
}

function StepCredentials({
  username,
  setUsername,
  password,
  setPassword,
  isCn,
  setIsCn,
  connecting,
  onNext,
  onCancel,
}: StepCredentialsProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="garmin-username">Garmin Username (Email)</Label>
        <Input
          id="garmin-username"
          type="text"
          placeholder="your.email@example.com"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={connecting}
          autoComplete="username"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="garmin-password">Garmin Password</Label>
        <Input
          id="garmin-password"
          type="password"
          placeholder="Enter your Garmin password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={connecting}
          autoComplete="current-password"
        />
      </div>
      <div className="space-y-2">
        <Label>Account Region</Label>
        <div className="flex gap-4">
          <div className="flex items-center gap-2">
            <input
              id="region-international"
              type="radio"
              name="garmin-region"
              checked={!isCn}
              onChange={() => setIsCn(false)}
              disabled={connecting}
              className="h-4 w-4"
            />
            <Label htmlFor="region-international" className="text-sm cursor-pointer">
              International (garmin.com)
            </Label>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="region-china"
              type="radio"
              name="garmin-region"
              checked={isCn}
              onChange={() => setIsCn(true)}
              disabled={connecting}
              className="h-4 w-4"
            />
            <Label htmlFor="region-china" className="text-sm cursor-pointer">
              China (garmin.cn)
            </Label>
          </div>
        </div>
      </div>
      <div className="flex gap-2">
        <Button
          onClick={onNext}
          disabled={connecting || !username || !password}
          variant="default"
          className="flex-1"
        >
          {connecting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Connecting...
            </>
          ) : (
            <>
              <ExternalLink className="h-4 w-4 mr-2" />
              Next
            </>
          )}
        </Button>
        <Button
          onClick={onCancel}
          disabled={connecting}
          variant="outline"
        >
          Cancel
        </Button>
      </div>
    </div>
  );
}

// Step 2: MFA Code
interface StepMfaProps {
  mfaToken: string;
  setMfaToken: (v: string) => void;
  connecting: boolean;
  onConfirm: () => void;
  onBack: () => void;
  isCn: boolean;
}

function StepMfa({
  mfaToken,
  setMfaToken,
  connecting,
  onConfirm,
  onBack,
  isCn,
}: StepMfaProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 p-4 bg-blue-50 dark:bg-blue-950 rounded-md border border-blue-200 dark:border-blue-800">
        <Mail className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
        <div className="text-sm text-blue-800 dark:text-blue-300">
          {isCn
            ? 'Garmin中国已向您的注册邮箱发送了验证码。请查收邮件并输入6位验证码。'
            : 'Garmin has sent a verification code to your registered email. Please check your email and enter the code.'}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="garmin-mfa">Email Verification Code</Label>
        <Input
          id="garmin-mfa"
          type="text"
          placeholder={isCn ? '输入邮箱中的6位验证码' : 'Enter 6-digit code from email'}
          value={mfaToken}
          onChange={(e) => setMfaToken(e.target.value)}
          disabled={connecting}
          maxLength={10}
          autoComplete="one-time-code"
          autoFocus
        />
        <p className="text-xs text-muted-foreground">
          {isCn
            ? '验证码仅在短时间内有效。如果您没有收到邮件，请检查垃圾邮件文件夹。'
            : 'The code is only valid for a short time. If you don\'t see the email, check your spam folder.'}
        </p>
      </div>

      <div className="flex gap-2">
        <Button
          onClick={onConfirm}
          disabled={connecting || !mfaToken}
          variant="default"
          className="flex-1"
        >
          {connecting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Verifying...
            </>
          ) : (
            <>
              <CheckCircle className="h-4 w-4 mr-2" />
              Verify & Connect
            </>
          )}
        </Button>
        <Button
          onClick={onBack}
          disabled={connecting}
          variant="outline"
        >
          Back
        </Button>
      </div>
    </div>
  );
}

export function GarminConnectionCard({ onSyncComplete }: GarminConnectionCardProps) {
  const [connection, setConnection] = useState<GarminConnection | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  // Login form state
  const [showLoginForm, setShowLoginForm] = useState(false);
  const [loginStep, setLoginStep] = useState<'credentials' | 'mfa'>('credentials');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mfaToken, setMfaToken] = useState('');
  const [isCn, setIsCn] = useState(false);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    fetchConnectionStatus();
  }, []);

  const fetchConnectionStatus = async () => {
    try {
      setLoading(true);
      const data = await getGarminConnection();
      setConnection(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch Garmin connection:', err);
      setError('Failed to load Garmin connection status');
    } finally {
      setLoading(false);
    }
  };

  // Step 1: Try to connect with credentials first
  const handleCredentialsSubmit = async () => {
    if (!username || !password) {
      setError('Please enter your Garmin username and password');
      return;
    }

    try {
      setError(null);
      setConnecting(true);

      // First attempt: try without MFA
      const data = await connectGarmin(username, password, undefined, isCn);
      handleConnectionSuccess(data);
    } catch (err: any) {
      console.error('First login attempt failed:', err);
      const errorMsg = err?.message || 'Failed to connect Garmin account';

      // Check if MFA is required
      if (err?.status === 400 || errorMsg.includes('MFA') || errorMsg.includes('2FA') || errorMsg.includes('OTP') || errorMsg.includes('authenticator')) {
        // Move to step 2: MFA code input
        setError(null);
        setLoginStep('mfa');
      } else if (err?.status === 401 || errorMsg.includes('401')) {
        if (isCn) {
          setError(
            'Invalid credentials for Garmin China. Please verify your username and password by logging into https://connect.garmin.cn.'
          );
        } else {
          setError(
            'Invalid Garmin credentials. Please verify your username and password by logging into https://connect.garmin.com.'
          );
        }
      } else {
        setError(`Failed to connect: ${errorMsg}`);
      }
    } finally {
      setConnecting(false);
    }
  };

  // Step 2: Submit with MFA code
  const handleMfaSubmit = async () => {
    if (!mfaToken) {
      setError('Please enter the verification code from your email');
      return;
    }

    try {
      setError(null);
      setConnecting(true);
      const data = await connectGarmin(username, password, mfaToken, isCn);
      handleConnectionSuccess(data);
    } catch (err: any) {
      console.error('MFA login failed:', err);
      const errorMsg = err?.message || 'Failed to connect Garmin account';

      if (err?.status === 401 || errorMsg.includes('401') || errorMsg.includes('Invalid') || errorMsg.includes('expired')) {
        setError(
          isCn
            ? '验证码无效或已过期。请重新获取验证码并重试。'
            : 'Invalid or expired verification code. Please request a new code and try again.'
        );
      } else {
        setError(`Failed to connect: ${errorMsg}`);
      }
    } finally {
      setConnecting(false);
    }
  };

  const handleConnectionSuccess = async (data: GarminConnection) => {
    setConnection(data);
    setShowLoginForm(false);
    setLoginStep('credentials');
    setSyncResult(
      isCn
        ? 'Garmin账号已连接！OAuth令牌已保存，以后将自动同步。'
        : 'Garmin account connected! OAuth tokens saved for automatic sync.'
    );
    setUsername('');
    setPassword('');
    setMfaToken('');
    setIsCn(false);
    // Trigger initial sync after connection
    await handleSync();
  };

  const handleUnlink = async () => {
    if (!confirm(
      isCn
        ? '确定要解除Garmin账号绑定吗？这将停止自动数据同步。'
        : 'Are you sure you want to unlink your Garmin account? This will stop automatic data sync.'
    )) {
      return;
    }

    try {
      setError(null);
      await unlinkGarmin();
      setConnection({
        connected: false,
        garmin_display_name: null,
        garmin_user_id: null,
        created_at: null,
        last_sync_at: null,
        sync_status: 'not_connected',
      });
      setSyncResult(
        isCn
          ? 'Garmin账号已解除绑定'
          : 'Garmin account unlinked successfully'
      );
    } catch (err) {
      console.error('Failed to unlink Garmin account:', err);
      setError('Failed to unlink Garmin account');
    }
  };

  const handleSync = async () => {
    try {
      setError(null);
      setSyncResult(null);
      setSyncing(true);
      const result = await syncGarmin(7);
      setConnection((prev) => ({
        ...prev!,
        last_sync_at: result.last_sync_at || new Date().toISOString(),
      }));

      if (result.success) {
        setSyncResult(
          isCn
            ? `同步完成：${result.days_synced} 天，${result.metrics_created} 条新数据，${result.metrics_updated} 条更新`
            : `Sync complete: ${result.days_synced} day(s) synced, ${result.metrics_created} new metrics, ${result.metrics_updated} updated`
        );
        onSyncComplete?.();
      } else {
        setError(
          isCn
            ? '同步完成但有错误，请检查数据。'
            : 'Sync completed with errors. Check your data.'
        );
      }
    } catch (err: any) {
      console.error('Failed to sync Garmin data:', err);
      const errorMsg = err?.message || 'Failed to sync Garmin data';

      // Check for authentication errors that might require reconnection
      if (errorMsg.includes('401') || errorMsg.includes('Unauthorized') || errorMsg.includes('authentication')) {
        setError(
          isCn
            ? '认证失败，您的Garmin会话可能已过期。请重新连接Garmin账号。'
            : 'Authentication failed. Your Garmin session may have expired. Please try reconnecting your Garmin account.'
        );
      } else {
        setError(isCn ? '同步失败，请重试。' : 'Failed to sync Garmin data. Please try again.');
      }
    } finally {
      setSyncing(false);
    }
  };

  const handleCancelLogin = () => {
    setShowLoginForm(false);
    setLoginStep('credentials');
    setError(null);
    setUsername('');
    setPassword('');
    setMfaToken('');
  };

  const handleBackToCredentials = () => {
    setLoginStep('credentials');
    setError(null);
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
              <ActivityIcon connected={isConnected} />
              Garmin Connect
            </CardTitle>
            <CardDescription>
              {isConnected
                ? (isCn
                    ? '从您的Garmin设备自动同步健康数据'
                    : 'Sync health data automatically from your Garmin device')
                : (isCn
                    ? '连接您的Garmin账号以同步健康数据'
                    : 'Connect your Garmin account to sync health data')
              }
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
                <span className="text-muted-foreground">
                  {isCn ? '显示名称' : 'Display Name'}
                </span>
                <span className="font-medium">
                  {connection.garmin_display_name || (isCn ? '未知' : 'Unknown')}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {isCn ? '状态' : 'Status'}
                </span>
                <StatusBadge status={connection.sync_status} isCn={isCn} />
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {isCn ? '上次同步' : 'Last Sync'}
                </span>
                <span className="font-medium">
                  {connection.last_sync_at
                    ? new Date(connection.last_sync_at).toLocaleString()
                    : (isCn ? '从未' : 'Never')}
                </span>
              </div>
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
                    {isCn ? '同步中...' : 'Syncing...'}
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    {isCn ? '立即同步' : 'Sync Now'}
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
                {isCn ? '解除绑定' : 'Unlink'}
              </Button>
            </div>
          </div>
        ) : showLoginForm ? (
          loginStep === 'credentials' ? (
            <StepCredentials
              username={username}
              setUsername={setUsername}
              password={password}
              setPassword={setPassword}
              isCn={isCn}
              setIsCn={setIsCn}
              connecting={connecting}
              onNext={handleCredentialsSubmit}
              onCancel={handleCancelLogin}
            />
          ) : (
            <StepMfa
              mfaToken={mfaToken}
              setMfaToken={setMfaToken}
              connecting={connecting}
              onConfirm={handleMfaSubmit}
              onBack={handleBackToCredentials}
              isCn={isCn}
            />
          )
        ) : (
          <Button
            onClick={() => setShowLoginForm(true)}
            disabled={loading || syncing}
            className="w-full"
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            {isCn ? '绑定Garmin账号' : 'Link Garmin Account'}
          </Button>
        )}

        <p className="text-xs text-muted-foreground">
          {isCn
            ? 'Garmin Connect集成可同步您的睡眠时长、静息心率、压力水平和锻炼时间。您的凭据已加密并安全存储。'
            : 'Garmin Connect integration syncs your sleep hours, resting heart rate, stress level, and exercise minutes. Your credentials are encrypted and stored securely.'}
        </p>
      </CardContent>
    </Card>
  );
}

function ActivityIcon({ connected }: { connected?: boolean }) {
  return (
    <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
      connected ? 'bg-green-100 dark:bg-green-900' : 'bg-muted'
    }`}>
      <svg
        className={`h-5 w-5 ${connected ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}`}
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
  );
}

function StatusBadge({ status, isCn }: { status: string; isCn?: boolean }) {
  const variants: Record<string, { label: string; className: string }> = {
    connected: {
      label: isCn ? '已连接' : 'Connected',
      className: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-400',
    },
    error: {
      label: isCn ? '错误' : 'Error',
      className: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-400',
    },
    expired: {
      label: isCn ? '已过期' : 'Expired',
      className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-400',
    },
    not_connected: {
      label: isCn ? '未连接' : 'Not Connected',
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
