'use client';

import { useEffect, useState } from 'react';
import { RefreshCw, Settings } from 'lucide-react';
import { ProtectedRoute } from '@/components/protected-route';
import { SiteHeader } from '@/components/site-header';
import {
  getDashboardSummary,
  getOverview,
  getTrends,
  updateHiddenCards,
  getUserPreferences,
} from '@/lib/api';
import {
  SummaryResponse,
  OverviewResponse,
  TrendResponse,
  UserPreference,
  CardId,
  CARD_IDS,
  User,
} from '@/types/api';
import { UserSummaryCard } from '@/components/dashboard/user-summary-card';
import { SleepCard } from '@/components/dashboard/sleep-card';
import { ActivityHealthCard } from '@/components/dashboard/activity-health-card';
import { WorkCard } from '@/components/dashboard/work-card';
import { StressCard } from '@/components/dashboard/stress-card';
import { TrendsCard } from '@/components/dashboard/trends-card';
import { FamilyMemberStrip } from '@/components/dashboard/family-member-strip';
import { MemberDetailPanel } from '@/components/dashboard/member-detail-panel';
import { CardSettingsPanel } from '@/components/dashboard/card-settings-panel';
import { DateNavigator } from '@/components/dashboard/date-navigator';
import { format } from 'date-fns';

export default function DashboardPage() {
  // Data states
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [trends, setTrends] = useState<TrendResponse | null>(null);
  const [members, setMembers] = useState<User[]>([]);

  // UI states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<User | null>(null);

  // Date navigation state
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());

  // Hidden cards state
  const [hiddenCards, setHiddenCards] = useState<Set<string>>(new Set());
  const [preferences, setPreferences] = useState<UserPreference | null>(null);

  // Fetch all data
  const fetchData = async (date?: Date) => {
    const targetDate = date || selectedDate;
    const dateStr = format(targetDate, 'yyyy-MM-dd');

    setLoading(true);
    setError(null);

    try {
      const [summaryData, overviewData, trendsData, prefsData] = await Promise.all([
        getDashboardSummary(dateStr),
        getOverview(dateStr),
        getTrends(30, dateStr),
        getUserPreferences(),
      ]);

      setSummary(summaryData);
      setOverview(overviewData);
      setTrends(trendsData);
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

      // Get current user
      const currentUser = prefsData.user_id;
      // Note: We would need to fetch family members separately
      // For now, we'll just set a placeholder
      setMembers([
        {
          id: currentUser,
          name: summaryData.user_name,
          email: '',
          avatar: summaryData.avatar,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Handle date change
  const handleDateChange = (date: Date) => {
    setSelectedDate(date);
    fetchData(date);
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
        <SiteHeader />
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
                onClick={() => fetchData(selectedDate)}
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
                  onClick={() => fetchData(selectedDate)}
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
              {/* User Summary Card */}
              <UserSummaryCard summary={summary} />

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

                {/* Activity/Health Card */}
                {!hiddenCards.has(CARD_IDS.ACTIVITY_HEALTH) && (
                  <ActivityHealthCard
                    metrics={overview.metrics}
                    hiddenCards={hiddenCards}
                    onToggleCard={(cardId, hidden) => handleToggleCard(cardId as CardId, hidden)}
                  />
                )}

                {/* Work Card */}
                {!hiddenCards.has(CARD_IDS.WORK) && (
                  <WorkCard
                    metrics={overview.metrics}
                    hiddenCards={hiddenCards}
                    onToggleCard={(cardId, hidden) => handleToggleCard(cardId as CardId, hidden)}
                  />
                )}

                {/* Stress Card */}
                {!hiddenCards.has(CARD_IDS.STRESS) && (
                  <StressCard
                    metrics={overview.metrics}
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
              {members.length > 1 && (
                <FamilyMemberStrip
                  members={members}
                  metrics={overview.metrics}
                  currentUserId={preferences?.user_id ?? 0}
                  onMemberClick={(userId) => {
                    const member = members.find((m) => m.id === userId);
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
