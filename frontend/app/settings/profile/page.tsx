// ABOUTME: User profile settings page for editing name and uploading avatar.
// ABOUTME: Supports JPG/PNG/WebP images up to 2MB.
'use client';

import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/contexts/auth-context';
import { ProtectedRoute } from '@/components/protected-route';
import { SiteHeader } from '@/components/site-header';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { uploadAvatar, updateProfile, getReportProfile, updateReportProfile } from '@/lib/api';
import { Camera, Loader2, ArrowLeft, CalendarIcon } from 'lucide-react';
import Link from 'next/link';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import type { UserProfile } from '@/types/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ProfilePage() {
  const { user, updateUser } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isSavingHealth, setIsSavingHealth] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Health profile state
  const [healthProfile, setHealthProfile] = useState<UserProfile | null>(null);
  const [birthDate, setBirthDate] = useState<Date | undefined>(undefined);
  const [gender, setGender] = useState<string>('');
  const [weightKg, setWeightKg] = useState<string>('');
  const [heightCm, setHeightCm] = useState<string>('');

  // Load health profile on mount
  useEffect(() => {
    const loadHealthProfile = async () => {
      try {
        const profile = await getReportProfile();
        setHealthProfile(profile);
        if (profile.birth_date) {
          setBirthDate(new Date(profile.birth_date));
        }
        if (profile.gender) {
          setGender(profile.gender);
        }
        if (profile.weight_kg !== null) {
          setWeightKg(profile.weight_kg.toString());
        }
        if (profile.height_cm !== null) {
          setHeightCm(profile.height_cm.toString());
        }
      } catch (err) {
        console.error('Failed to load health profile:', err);
      }
    };
    loadHealthProfile();
  }, []);

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

  const handleSaveHealthProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSavingHealth(true);

    try {
      const updateData: Record<string, any> = {};

      if (birthDate) {
        updateData.birth_date = format(birthDate, 'yyyy-MM-dd');
      }
      if (gender) {
        updateData.gender = gender;
      }
      if (weightKg) {
        const weight = parseFloat(weightKg);
        if (!isNaN(weight)) {
          updateData.weight_kg = weight;
        }
      }
      if (heightCm) {
        const height = parseFloat(heightCm);
        if (!isNaN(height)) {
          updateData.height_cm = height;
        }
      }

      const updated = await updateReportProfile(updateData);
      setHealthProfile(updated);
      setSuccess('健康画像已保存');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || '保存失败');
    } finally {
      setIsSavingHealth(false);
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

            {/* Health Profile Section */}
            <div className="pt-6 border-t">
              <h2 className="text-xl font-semibold mb-4">健康画像</h2>
              <p className="text-sm text-muted-foreground mb-6">
                用于个性化晨间报告和夜晚报告
              </p>

              <form onSubmit={handleSaveHealthProfile} className="space-y-4">
                {/* Birth Date */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    出生日期
                  </label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <button
                        type="button"
                        className="w-full px-4 py-2 rounded-lg border bg-background text-left flex items-center justify-between hover:bg-accent"
                      >
                        {birthDate ? (
                          format(birthDate, 'yyyy年M月d日', { locale: zhCN })
                        ) : (
                          <span className="text-muted-foreground">选择出生日期</span>
                        )}
                        <CalendarIcon className="h-4 w-4 text-muted-foreground" />
                      </button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={birthDate}
                        onSelect={setBirthDate}
                        initialFocus
                        defaultMonth={birthDate || new Date(1990, 0, 1)}
                        fromYear={1920}
                        toYear={new Date().getFullYear()}
                        captionLayout="dropdown"
                      />
                    </PopoverContent>
                  </Popover>
                  {healthProfile?.age !== null && healthProfile?.age !== undefined && (
                    <p className="text-xs text-muted-foreground mt-1">
                      年龄: {healthProfile.age} 岁
                    </p>
                  )}
                </div>

                {/* Gender */}
                <div>
                  <label htmlFor="gender" className="block text-sm font-medium mb-2">
                    性别
                  </label>
                  <select
                    id="gender"
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="">请选择</option>
                    <option value="male">男</option>
                    <option value="female">女</option>
                    <option value="other">其他</option>
                  </select>
                </div>

                {/* Weight */}
                <div>
                  <label htmlFor="weight" className="block text-sm font-medium mb-2">
                    体重 (kg)
                  </label>
                  <input
                    id="weight"
                    type="number"
                    step="0.1"
                    min="20"
                    max="300"
                    value={weightKg}
                    onChange={(e) => setWeightKg(e.target.value)}
                    className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="输入体重"
                  />
                </div>

                {/* Height */}
                <div>
                  <label htmlFor="height" className="block text-sm font-medium mb-2">
                    身高 (cm)
                  </label>
                  <input
                    id="height"
                    type="number"
                    step="0.1"
                    min="50"
                    max="300"
                    value={heightCm}
                    onChange={(e) => setHeightCm(e.target.value)}
                    className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="输入身高"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isSavingHealth}
                  className="px-6 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isSavingHealth && <Loader2 className="h-4 w-4 animate-spin" />}
                  保存健康画像
                </button>
              </form>
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
