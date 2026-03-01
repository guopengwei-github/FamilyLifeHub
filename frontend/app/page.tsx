'use client';

import { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Settings } from 'lucide-react';
import { ProtectedRoute } from '@/components/protected-route';
import { SiteHeader } from '@/components/site-header';
import { useAuth } from '@/contexts/auth-context';
import {
  getDashboardSummary,
  getOverview,
  getTrends,
  updateHiddenCards,
  getUserPreferences,
  listUsers,
  getGarminConnection,
  syncGarmin,
} from '@/lib/api';
import {
  SummaryResponse,
  OverviewResponse,
  TrendResponse,
  UserPreference,
  CardId,
  CARD_IDS,
  User,
  GarminConnection,
} from '@/types/api';
import { UserSummaryCard } from '@/components/dashboard/user-summary-card';
import { SleepCard } from '@/components/dashboard/sleep-card';
import { ActivityCard } from '@/components/dashboard/activity-card';
import { BodyStatusCard } from '@/components/dashboard/body-status-card';
import { HRVCard } from '@/components/dashboard/hrv-card';
import { TrendsCard } from '@/components/dashboard/trends-card';
import { FamilyMemberStrip } from '@/components/dashboard/family-member-strip';
import { MemberDetailPanel } from '@/components/dashboard/member-detail-panel';
import { CardSettingsPanel } from '@/components/dashboard/card-settings-panel';
import { DateNavigator } from '@/components/dashboard/date-navigator';
import { MorningReport, EveningReport } from '@/components/reports';
import { format, isToday } from 'date-fns';
import { useRouter } from 'next/navigation';

// Garmin sync status types
type GarminSyncStatus = 'not_connected' | 'fresh' | 'stale' | 'severely_stale' | 'syncing' | 'error';

interface GarminSyncState {
  status: GarminSyncStatus;
  hoursAgo?: number;
  lastSyncAt?: Date | null;
}

export default function DashboardPage() {
  const router = useRouter();
  // Auth state
  const { user: authUser } = useAuth();

  // Data states
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [trends, setTrends] = useState<TrendResponse | null>(null);
  const [allUsers, setAllUsers] = useState<User[]>([]);

  // Garmin sync state
  const [garminSyncState, setGarminSyncState] = useState<GarminSyncState>({ status: 'not_connected' });

  // User states
  const [viewingUser, setViewingUser] = useState<User | null>(null);

  // UI states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<User | null>(null);

  // Date navigation state - default to yesterday since Garmin sleep data has delay
  const [selectedDate, setSelectedDate] = useState<Date>(() => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday;
  });

  // Hidden cards state
  const [hiddenCards, setHiddenCards] = useState<Set<string>>(new Set());
  const [preferences, setPreferences] = useState<UserPreference | null>(null);

  // Fetch all users
  const fetchAllUsers = async () => {
    try {
      const users = await listUsers();
      setAllUsers(users);
      return users;
    } catch (err) {
      console.error('Error fetching users:', err);
      return [];
    }
  };

  // Calculate Garmin sync status from connection
  const calculateGarminSyncState = (connection: GarminConnection): GarminSyncState => {
    if (!connection.connected) {
      return { status: 'not_connected' };
    }

    if (!connection.last_sync_at) {
      return { status: 'stale' };
    }

    // Parse last_sync_at - if no timezone, treat as UTC (backend stores UTC)
    const lastSyncStr = connection.last_sync_at;
    const lastSyncWithTz = lastSyncStr.includes('+') || lastSyncStr.includes('Z')
      ? lastSyncStr
      : lastSyncStr + '+00:00';  // Add UTC timezone if missing

    const now = new Date();
    const lastSync = new Date(lastSyncWithTz);
    const hoursDiff = (now.getTime() - lastSync.getTime()) / (1000 * 60 * 60);

    if (hoursDiff < 24) {
      return { status: 'fresh', hoursAgo: hoursDiff, lastSyncAt: lastSync };
    } else if (hoursDiff >= 72) {
      return { status: 'severely_stale', hoursAgo: hoursDiff, lastSyncAt: lastSync };
    } else {
      return { status: 'stale', hoursAgo: hoursDiff, lastSyncAt: lastSync };
    }
  };

  // Fetch Garmin connection status
  const fetchGarminConnection = async () => {
    try {
      const connection = await getGarminConnection();
      setGarminSyncState(calculateGarminSyncState(connection));
    } catch (err) {
      console.error('Error fetching Garmin connection:', err);
      setGarminSyncState({ status: 'not_connected' });
    }
  };

  // Handle Garmin sync
  const handleGarminSync = async () => {
    setGarminSyncState((prev) => ({ ...prev, status: 'syncing' }));

    try {
      await syncGarmin(7);
      // Refresh Garmin connection state
      await fetchGarminConnection();
      // Refresh dashboard data
      if (viewingUser) {
        await fetchUserData(viewingUser, selectedDate);
      }
    } catch (err) {
      console.error('Error syncing Garmin:', err);
      setGarminSyncState((prev) => ({ ...prev, status: 'error' }));
    }
  };

  // Fetch user data for a specific user
  const fetchUserData = useCallback(async (user: User, date?: Date) => {
    const targetDate = date || selectedDate;
    const dateStr = format(targetDate, 'yyyy-MM-dd');
    setLoading(true);
    setError(null);

    try {
      const [summaryData, overviewData, trendsData] = await Promise.all([
        getDashboardSummary(dateStr, user.id),
        getOverview(dateStr, user.id),
        getTrends(30, dateStr, user.id),
      ]);

      setSummary(summaryData);
      setOverview(overviewData);
      setTrends(trendsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  // Fetch preferences
  const fetchPreferences = async () => {
    try {
      const prefsData = await getUserPreferences();
      setPreferences(prefsData);

      // Parse hidden cards from preferences
      const hiddenSet = new Set<string>();
      if (prefsData.hidden_cards) {
        try {
          const parsed = JSON.parse(prefsData.hidden_cards);
          parsed.forEach((cardId: string) => hiddenSet.add(cardId));
        } catch {
          // Invalid JSON, ignore
        }
      }
      setHiddenCards(hiddenSet);
    } catch (err) {
      console.error('Error fetching preferences:', err);
    }
  };

  // Handle viewing user change
  const handleViewingUserChange = (user: User) => {
    setViewingUser(user);
  };

  // Initialize: fetch preferences and all users
  useEffect(() => {
    const init = async () => {
      if (!authUser) return;

      // Fetch preferences
      await fetchPreferences();

      // Fetch all users
      const users = await fetchAllUsers();

      // Set viewing user to current user if not already set
      if (!viewingUser) {
        setViewingUser(authUser);
      }

      // Fetch Garmin connection status
      await fetchGarminConnection();
    };
    init();
  }, [authUser]);

  // Refetch data when viewingUser or selectedDate changes
  useEffect(() => {
    if (viewingUser) {
      fetchUserData(viewingUser, selectedDate);
    }
  }, [viewingUser, selectedDate]);

  // Handle date change
  const handleDateChange = (date: Date) => {
    setSelectedDate(date);
    // Data will be refetched by the useEffect when selectedDate changes
  };

  // Handle toggle card visibility
  const handleToggleCard = async (cardId: CardId, hidden: boolean) => {
    // Optimistically update local state
    const newHiddenCards = new Set(hiddenCards);
    if (hidden) {
      newHiddenCards.add(cardId);
    } else {
      newHiddenCards.delete(cardId);
    }
    setHiddenCards(newHiddenCards);

    try {
      const hiddenCardsJson = JSON.stringify(Array.from(newHiddenCards));
      await updateHiddenCards(hiddenCardsJson);
    } catch (err) {
      // Revert on error
      setHiddenCards(new Set(hiddenCards));
      console.error('Failed to update hidden cards:', err);
    }
  };

  // Handle member click
  const handleMemberClick = (user: User) => {
    setSelectedMember(user);
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen">
        <SiteHeader
          users={allUsers}
          viewingUser={viewingUser}
          onViewingUserChange={handleViewingUserChange}
          showUserSwitcher={true}
        />
        <main className="container mx-auto py-8 space-y-8">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold tracking-tight">家庭数据看板</h1>
              <p className="text-muted-foreground">
                追踪和分析您家庭的健康和工作数据
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setSettingsOpen(true)}
                className="flex items-center gap-2 px-4 py-2 border rounded-md hover:bg-muted transition-colors"
              >
                <Settings className="h-4 w-4" />
                显示设置
              </button>
              <button
                onClick={() => viewingUser && fetchUserData(viewingUser, selectedDate)}
                className="flex items-center gap-2 px-4 py-2 border rounded-md hover:bg-muted transition-colors"
                disabled={loading}
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                刷新
              </button>
            </div>
          </div>

          {/* Date Navigator */}
          <DateNavigator
            selectedDate={selectedDate}
            onDateChange={handleDateChange}
            loading={loading}
          />

          {/* Loading State */}
          {loading && !summary && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4" />
                <p className="text-muted-foreground">加载看板数据...</p>
              </div>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <p className="text-red-500 mb-4">错误: {error}</p>
                <button
                  onClick={() => viewingUser && fetchUserData(viewingUser, selectedDate)}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
                >
                  重试
                </button>
              </div>
            </div>
          )}

          {/* Main Content */}
          {!loading && !error && summary && overview && (
            <div className="space-y-8">
              {/* Health Reports - Only show for today */}
              {isToday(selectedDate) && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <MorningReport date={format(selectedDate, 'yyyy-MM-dd')} />
                  <EveningReport date={format(selectedDate, 'yyyy-MM-dd')} />
                </div>
              )}

              {/* User Summary Card */}
              <UserSummaryCard
                summary={summary}
                currentUser={authUser}
                viewingUser={viewingUser}
                garminSyncState={garminSyncState}
                onGarminSync={handleGarminSync}
              />

              {/* Dashboard Cards Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Sleep Card */}
                {!hiddenCards.has(CARD_IDS.SLEEP) && (
                  <SleepCard
                    metrics={overview.metrics}
                    hiddenCards={hiddenCards}
                    onToggleCard={(cardId, hidden) => handleToggleCard(cardId as CardId, hidden)}
                  />
                )}

                {/* Activity Card */}
                {!hiddenCards.has(CARD_IDS.ACTIVITY) && (
                  <ActivityCard
                    metrics={overview.metrics}
                    userId={viewingUser?.id}
                    date={format(selectedDate, 'yyyy-MM-dd')}
                    hiddenCards={hiddenCards}
                    onToggleCard={(cardId, hidden) => handleToggleCard(cardId as CardId, hidden)}
                  />
                )}

                {/* Body Status Card */}
                {!hiddenCards.has(CARD_IDS.BODY_STATUS) && (
                  <BodyStatusCard
                    metrics={overview.metrics}
                    userId={viewingUser?.id}
                    date={format(selectedDate, 'yyyy-MM-dd')}
                    hiddenCards={hiddenCards}
                    onToggleCard={(cardId, hidden) => handleToggleCard(cardId as CardId, hidden)}
                  />
                )}

                {/* HRV Card */}
                {!hiddenCards.has(CARD_IDS.HRV) && (
                  <HRVCard
                    metrics={overview.metrics}
                    trends={trends?.data ?? []}
                    hiddenCards={hiddenCards}
                    onToggleCard={(cardId, hidden) => handleToggleCard(cardId as CardId, hidden)}
                  />
                )}
              </div>

              {/* Trends Card - Full Width */}
              {!hiddenCards.has(CARD_IDS.TRENDS) && (
                <TrendsCard
                  trends={trends}
                  hiddenCards={hiddenCards}
                  onToggleCard={(cardId, hidden) => handleToggleCard(cardId as CardId, hidden)}
                />
              )}

              {/* Family Member Strip */}
              {allUsers.length > 1 && (
                <FamilyMemberStrip
                  members={allUsers}
                  metrics={overview.metrics}
                  currentUserId={authUser?.id ?? 0}
                  onMemberClick={(userId) => {
                    const member = allUsers.find((m) => m.id === userId);
                    if (member) handleMemberClick(member);
                  }}
                />
              )}
            </div>
          )}
        </main>
      </div>

      {/* Card Settings Panel */}
      <CardSettingsPanel
        isOpen={settingsOpen}
        hiddenCards={hiddenCards}
        onClose={() => setSettingsOpen(false)}
        onToggleCard={handleToggleCard}
      />

      {/* Member Detail Panel */}
      <MemberDetailPanel
        user={selectedMember}
        metrics={overview?.metrics ?? []}
        allMetrics={overview?.metrics ?? []}
        isOpen={selectedMember !== null}
        onClose={() => setSelectedMember(null)}
      />
    </ProtectedRoute>
  );
}
