// ABOUTME: User profile settings page for editing name and uploading avatar.
// ABOUTME: Supports JPG/PNG/WebP images up to 2MB.
'use client';

import { useState, useRef } from 'react';
import { useAuth } from '@/contexts/auth-context';
import { ProtectedRoute } from '@/components/protected-route';
import { SiteHeader } from '@/components/site-header';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { uploadAvatar, updateProfile } from '@/lib/api';
import { Camera, Loader2, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ProfilePage() {
  const { user, updateUser } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const getAvatarUrl = (avatar: string | null | undefined) => {
    if (!avatar) return undefined;
    if (avatar.startsWith('http')) return avatar;
    return `${API_URL}${avatar}`;
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setIsUploading(true);

    try {
      const updatedUser = await uploadAvatar(file);
      updateUser(updatedUser);
      setSuccess('头像已更新');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || '上传失败');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleSaveName = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || name === user?.name) return;

    setError(null);
    setIsSaving(true);

    try {
      const updatedUser = await updateProfile({ name: name.trim() });
      updateUser(updatedUser);
      setSuccess('姓名已更新');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || '保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background">
        <SiteHeader />

        <main className="container mx-auto px-4 py-8 max-w-2xl">
          <Link
            href="/settings"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6"
          >
            <ArrowLeft className="h-4 w-4" />
            返回设置
          </Link>

          <h1 className="text-3xl font-bold mb-8">个人资料</h1>

          {error && (
            <div className="mb-6 p-4 rounded-lg bg-destructive/10 text-destructive">
              {error}
            </div>
          )}

          {success && (
            <div className="mb-6 p-4 rounded-lg bg-green-500/10 text-green-600">
              {success}
            </div>
          )}

          <div className="space-y-8">
            {/* Avatar Section */}
            <div className="flex flex-col items-center gap-4">
              <div className="relative group">
                <Avatar className="h-32 w-32 cursor-pointer" onClick={handleAvatarClick}>
                  <AvatarImage src={getAvatarUrl(user?.avatar)} />
                  <AvatarFallback className="text-4xl">
                    {user?.name?.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div
                  className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                  onClick={handleAvatarClick}
                >
                  {isUploading ? (
                    <Loader2 className="h-8 w-8 text-white animate-spin" />
                  ) : (
                    <Camera className="h-8 w-8 text-white" />
                  )}
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                点击头像更换（支持 JPG、PNG、WebP，最大 2MB）
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".jpg,.jpeg,.png,.webp"
                className="hidden"
                onChange={handleFileChange}
              />
            </div>

            {/* Name Section */}
            <form onSubmit={handleSaveName} className="space-y-4">
              <div>
                <label htmlFor="name" className="block text-sm font-medium mb-2">
                  姓名
                </label>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="输入姓名"
                  maxLength={100}
                />
              </div>
              <button
                type="submit"
                disabled={isSaving || !name.trim() || name === user?.name}
                className="px-6 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSaving && <Loader2 className="h-4 w-4 animate-spin" />}
                保存
              </button>
            </form>

            {/* Email (read-only) */}
            <div>
              <label className="block text-sm font-medium mb-2">
                邮箱
              </label>
              <p className="px-4 py-2 rounded-lg border bg-muted text-muted-foreground">
                {user?.email}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                邮箱不可修改
              </p>
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
