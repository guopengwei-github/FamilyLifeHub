'use client';

import { useState, useEffect } from 'react';
import { ProtectedRoute } from '@/components/protected-route';
import { SiteHeader } from '@/components/site-header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import Link from 'next/link';
import { ArrowLeft, Mail, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

interface SMTPConfig {
  smtp_server: string;
  smtp_port: number;
  username: string;
  password: string;
  sender_name: string;
}

interface NotificationSettings {
  notification_emails: string[];
}

export default function EmailSettingsPage() {
  const [smtpConfig, setSMTPConfig] = useState<SMTPConfig>({
    smtp_server: '',
    smtp_port: 587,
    username: '',
    password: '',
    sender_name: '',
  });

  const [notificationEmails, setNotificationEmails] = useState<string[]>([]);
  const [newEmail, setNewEmail] = useState('');
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = {
        'Authorization': `Bearer ${token}`,
      };

      const [smtpRes, notifRes] = await Promise.all([
        fetch('http://localhost:8000/api/v1/smtp-config', { headers }),
        fetch('http://localhost:8000/api/v1/notification-settings', { headers }),
      ]);

      if (smtpRes.ok) {
        const smtpData = await smtpRes.json();
        if (smtpData) {
          setSMTPConfig({
            smtp_server: smtpData.smtp_host || '',
            smtp_port: smtpData.smtp_port || 465,
            username: smtpData.smtp_user || '',
            password: '',
            sender_name: smtpData.sender_name || '',
          });
        }
      }

      if (notifRes.ok) {
        const notifData = await notifRes.json();
        const email = notifData.mail_for_notification;
        setNotificationEmails(email ? [email] : []);
      }
    } catch (error) {
      console.error('Failed to fetch configs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSMTP = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const method = 'PUT';
      const response = await fetch('http://localhost:8000/api/v1/smtp-config', {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          smtp_host: smtpConfig.smtp_server,
          smtp_port: smtpConfig.smtp_port,
          smtp_user: smtpConfig.username,
          smtp_password: smtpConfig.password,
          use_ssl: smtpConfig.smtp_port === 465,
          sender_name: smtpConfig.sender_name,
        }),
      });

      if (response.ok) {
        alert('SMTP configuration saved successfully!');
      } else {
        const error = await response.json();
        alert(`Failed to save: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      alert('Failed to save SMTP configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/api/v1/smtp-config/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      const data = await response.json();
      setTestResult({
        success: response.ok,
        message: data.message || data.detail || 'Connection test completed',
      });
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Failed to test connection',
      });
    } finally {
      setTesting(false);
    }
  };

  const handleAddEmail = () => {
    if (newEmail && !notificationEmails.includes(newEmail)) {
      setNotificationEmails([...notificationEmails, newEmail]);
      setNewEmail('');
    }
  };

  const handleRemoveEmail = (email: string) => {
    setNotificationEmails(notificationEmails.filter(e => e !== email));
  };

  const handleSaveNotificationEmails = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const primaryEmail = notificationEmails[0] || null;
      const response = await fetch('http://localhost:8000/api/v1/notification-settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ mail_for_notification: primaryEmail }),
      });

      if (response.ok) {
        alert('Notification email saved successfully!');
      } else {
        const error = await response.json();
        alert(`Failed to save: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      alert('Failed to save notification email');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-background">
          <SiteHeader />
          <main className="container mx-auto px-4 py-8 max-w-4xl">
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          </main>
        </div>
      </ProtectedRoute>
    );
  }

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
              <Mail className="h-6 w-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">Email Settings</h1>
              <p className="text-muted-foreground">
                Configure SMTP settings and notification recipients
              </p>
            </div>
          </div>

          <div className="space-y-6">
            {/* SMTP Configuration Card */}
            <div className="rounded-lg border p-6 space-y-4">
              <h2 className="text-lg font-semibold">SMTP Configuration</h2>
              <p className="text-sm text-muted-foreground">
                Configure your email server settings for sending notifications
              </p>

              <div className="grid gap-4">
                <div className="grid gap-2">
                  <label htmlFor="smtp_server" className="text-sm font-medium">
                    SMTP Server
                  </label>
                  <Input
                    id="smtp_server"
                    placeholder="smtp.qq.com"
                    value={smtpConfig.smtp_server}
                    onChange={(e) => setSMTPConfig({ ...smtpConfig, smtp_server: e.target.value })}
                  />
                </div>

                <div className="grid gap-2">
                  <label htmlFor="smtp_port" className="text-sm font-medium">
                    Port
                  </label>
                  <Input
                    id="smtp_port"
                    type="number"
                    placeholder="465"
                    value={smtpConfig.smtp_port}
                    onChange={(e) => setSMTPConfig({ ...smtpConfig, smtp_port: parseInt(e.target.value) || 465 })}
                  />
                </div>

                <div className="grid gap-2">
                  <label htmlFor="username" className="text-sm font-medium">
                    Username
                  </label>
                  <Input
                    id="username"
                    placeholder="your-email@qq.com"
                    value={smtpConfig.username}
                    onChange={(e) => setSMTPConfig({ ...smtpConfig, username: e.target.value })}
                  />
                </div>

                <div className="grid gap-2">
                  <label htmlFor="password" className="text-sm font-medium">
                    Password / Authorization Code
                  </label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={smtpConfig.password}
                    onChange={(e) => setSMTPConfig({ ...smtpConfig, password: e.target.value })}
                  />
                  <p className="text-xs text-muted-foreground">
                    For QQ Mail, Gmail, etc., use the app-specific authorization code instead of your password
                  </p>
                </div>

                <div className="grid gap-2">
                  <label htmlFor="sender_name" className="text-sm font-medium">
                    Sender Name
                  </label>
                  <Input
                    id="sender_name"
                    placeholder="Family Life Hub"
                    value={smtpConfig.sender_name}
                    onChange={(e) => setSMTPConfig({ ...smtpConfig, sender_name: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <Button onClick={handleSaveSMTP} disabled={saving}>
                  {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  Save Configuration
                </Button>
                <Button variant="outline" onClick={handleTestConnection} disabled={testing}>
                  {testing && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  Test Connection
                </Button>
              </div>

              {/* Test Result */}
              {testResult && (
                <div className={`flex items-start gap-2 p-4 rounded-lg ${
                  testResult.success 
                    ? 'bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800' 
                    : 'bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800'
                }`}>
                  {testResult.success ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5" />
                  )}
                  <div>
                    <p className={`font-medium ${
                      testResult.success 
                        ? 'text-green-800 dark:text-green-200' 
                        : 'text-red-800 dark:text-red-200'
                    }`}>
                      {testResult.success ? 'Connection Successful' : 'Connection Failed'}
                    </p>
                    <p className={`text-sm ${
                      testResult.success 
                        ? 'text-green-700 dark:text-green-300' 
                        : 'text-red-700 dark:text-red-300'
                    }`}>
                      {testResult.message}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Notification Emails Card */}
            <div className="rounded-lg border p-6 space-y-4">
              <h2 className="text-lg font-semibold">Notification Recipient</h2>
              <p className="text-sm text-muted-foreground">
                Email address that will receive health report notifications
              </p>

              <div className="space-y-3">
                {notificationEmails.length > 0 ? (
                  notificationEmails.map((email) => (
                    <div key={email} className="flex items-center justify-between p-3 rounded-lg bg-muted">
                      <span className="text-sm">{email}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveEmail(email)}
                        className="text-destructive hover:text-destructive"
                      >
                        Remove
                      </Button>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground italic">
                    No notification email configured
                  </p>
                )}
              </div>

              <div className="flex gap-2">
                <Input
                  type="email"
                  placeholder="email@example.com"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddEmail()}
                />
                <Button variant="outline" onClick={handleAddEmail} disabled={!newEmail}>
                  Add
                </Button>
              </div>

              <div className="pt-4">
                <Button onClick={handleSaveNotificationEmails} disabled={saving}>
                  {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  Save Recipient
                </Button>
              </div>
            </div>

            {/* Information Card */}
            <div className="rounded-lg border p-6 space-y-4">
              <h2 className="text-lg font-semibold">Email Setup Guide</h2>
              
              <div className="space-y-3 text-sm">
                <div>
                  <h3 className="font-medium mb-1">QQ Mail Setup</h3>
                  <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                    <li>Go to QQ Mail Settings → Account → POP3/SMTP Service</li>
                    <li>Enable SMTP service and generate an authorization code</li>
                    <li>Use the authorization code as your password</li>
                    <li>SMTP Server: smtp.qq.com, Port: 465 (SSL)</li>
                  </ol>
                </div>

                <div className="pt-3 border-t">
                  <h3 className="font-medium mb-1">Gmail Setup</h3>
                  <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                    <li>Enable 2-Factor Authentication on your Google account</li>
                    <li>Generate an App Password: Google Account → Security → App passwords</li>
                    <li>Use the generated 16-character code as your password</li>
                    <li>SMTP Server: smtp.gmail.com, Port: 587</li>
                  </ol>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
