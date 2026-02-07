'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  getStravaActivities,
} from '@/lib/api';
import {
  StravaActivity,
  StravaActivitiesResponse,
} from '@/types/api';
import {
  Loader2,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Clock,
  Flame,
  Heart,
  Mountain,
  Bike,
  Droplets,
} from 'lucide-react';

interface StravaActivitiesPanelProps {
  onActivityClick?: (activity: StravaActivity) => void;
}

// Activity type icons mapping
const activityIcons: Record<string, React.ReactNode> = {
  Run: <Mountain className="h-4 w-4" />,
  Ride: <Bike className="h-4 w-4" />,
  Swim: <Droplets className="h-4 w-4" />,
  default: <MapPin className="h-4 w-4" />,
};

// Activity type colors mapping
const activityColors: Record<string, string> = {
  Run: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-400',
  Ride: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-400',
  Swim: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-400',
  default: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
};

export function StravaActivitiesPanel({ onActivityClick }: StravaActivitiesPanelProps) {
  const [activities, setActivities] = useState<StravaActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [activityType, setActivityType] = useState<string | null>(null);
  const pageSize = 10;

  useEffect(() => {
    fetchActivities();
  }, [activityType, page]);

  const fetchActivities = async () => {
    try {
      setLoading(true);
      setError(null);
      const data: StravaActivitiesResponse = await getStravaActivities(
        undefined,
        undefined,
        100, // Fetch more to support filtering
        activityType || undefined
      );
      setActivities(data.activities);
      setTotalCount(data.count);
    } catch (err: any) {
      console.error('Failed to fetch Strava activities:', err);
      setError(err?.message || 'Failed to load activities');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setPage(0);
    await fetchActivities();
  };

  const getActivityIcon = (type: string | null) => {
    return activityIcons[type || 'default'] || activityIcons.default;
  };

  const getActivityColor = (type: string | null) => {
    return activityColors[type || 'default'] || activityColors.default;
  };

  const formatDistance = (meters: number | null) => {
    if (meters === null) return '--';
    if (meters < 1000) {
      return `${meters.toFixed(0)}m`;
    }
    return `${(meters / 1000).toFixed(2)}km`;
  };

  const formatDuration = (seconds: number | null) => {
    if (seconds === null) return '--';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '--';
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatPace = (activity: StravaActivity) => {
    if (!activity.distance_meters || !activity.moving_time_seconds) {
      return '--';
    }
    const pace = activity.moving_time_seconds / (activity.distance_meters / 1000); // min/km
    const minutes = Math.floor(pace);
    const seconds = Math.round((pace - minutes) * 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')} /km`;
  };

  const paginatedActivities = activities.slice(page * pageSize, (page + 1) * pageSize);
  const totalPages = Math.ceil(activities.length / pageSize);
  const uniqueActivityTypes = Array.from(
    new Set(activities.map((a) => a.activity_type).filter(Boolean) as string[])
  ).sort();

  if (loading && activities.length === 0) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" />
              Activities
            </CardTitle>
            <CardDescription>
              {totalCount > 0 ? `${totalCount} synced activit${totalCount === 1 ? 'y' : 'ies'}` : 'No synced activities'}
            </CardDescription>
          </div>
          <Button
            onClick={handleRefresh}
            disabled={refreshing}
            variant="outline"
            size="icon"
          >
            {refreshing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 p-3 rounded-md">
            <span>{error}</span>
          </div>
        )}

        {uniqueActivityTypes.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <Badge
              variant={activityType === null ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => setActivityType(null)}
            >
              All
            </Badge>
            {uniqueActivityTypes.map((type) => (
              <Badge
                key={type}
                variant={activityType === type ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => {
                  setActivityType(type);
                  setPage(0);
                }}
              >
                {type}
              </Badge>
            ))}
          </div>
        )}

        {activities.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <MapPin className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No activities synced yet</p>
            <p className="text-sm mt-1">Connect your Strava account and sync to see your activities</p>
          </div>
        ) : (
          <div className="space-y-3">
            {paginatedActivities.map((activity) => (
              <div
                key={activity.id}
                className="rounded-lg border p-4 hover:bg-accent cursor-pointer transition-colors"
                onClick={() => onActivityClick?.(activity)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className={`h-10 w-10 rounded-full flex items-center justify-center flex-shrink-0 ${getActivityColor(activity.activity_type)}`}>
                      {getActivityIcon(activity.activity_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium truncate">
                          {activity.name || `${activity.activity_type} Activity`}
                        </h4>
                        {activity.activity_type && (
                          <Badge variant="outline" className="text-xs">
                            {activity.activity_type}
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">
                        {formatDate(activity.date)}
                      </p>
                      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {formatDistance(activity.distance_meters)}
                        </div>
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDuration(activity.moving_time_seconds)}
                        </div>
                        {activity.calories && (
                          <div className="flex items-center gap-1">
                            <Flame className="h-3 w-3" />
                            {Math.round(activity.calories)} cal
                          </div>
                        )}
                        {activity.average_heartrate && (
                          <div className="flex items-center gap-1">
                            <Heart className="h-3 w-3" />
                            {Math.round(activity.average_heartrate)} bpm
                          </div>
                        )}
                        {activity.activity_type && ['Run', 'Ride', 'Walk'].includes(activity.activity_type) && (
                          <div className="flex items-center gap-1">
                            <span>🏃 {formatPace(activity)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 pt-2">
            <Button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || refreshing}
              variant="outline"
              size="icon"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm text-muted-foreground">
              Page {page + 1} of {totalPages}
            </span>
            <Button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1 || refreshing}
              variant="outline"
              size="icon"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Helper component for activity detail modal
export interface ActivityDetailProps {
  activity: StravaActivity | null;
  onClose: () => void;
}

export function ActivityDetail({ activity, onClose }: ActivityDetailProps) {
  if (!activity) return null;

  const formatDistance = (meters: number | null) => {
    if (meters === null) return '--';
    if (meters < 1000) {
      return `${meters.toFixed(0)}m`;
    }
    return `${(meters / 1000).toFixed(2)}km`;
  };

  const formatDuration = (seconds: number | null) => {
    if (seconds === null) return '--';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    }
    return `${minutes}m ${secs}s`;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '--';
    return new Date(dateStr).toLocaleString(undefined, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatSpeed = (mps: number | null) => {
    if (mps === null) return '--';
    return `${(mps * 3.6).toFixed(1)} km/h`;
  };

  const formatPace = (activity: StravaActivity) => {
    if (!activity.distance_meters || !activity.moving_time_seconds) {
      return '--';
    }
    const pace = activity.moving_time_seconds / (activity.distance_meters / 1000); // min/km
    const minutes = Math.floor(pace);
    const seconds = Math.round((pace - minutes) * 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')} /km`;
  };

  const details = [
    { label: 'Activity Type', value: activity.activity_type || '--', icon: getActivityIcon(activity.activity_type) },
    { label: 'Date', value: formatDate(activity.start_date_local || activity.start_date), icon: null },
    { label: 'Distance', value: formatDistance(activity.distance_meters), icon: null },
    { label: 'Moving Time', value: formatDuration(activity.moving_time_seconds), icon: null },
    { label: 'Elapsed Time', value: formatDuration(activity.elapsed_time_seconds), icon: null },
    { label: 'Average Speed', value: formatSpeed(activity.average_speed_mps), icon: null },
    { label: 'Max Speed', value: formatSpeed(activity.max_speed_mps), icon: null },
    { label: 'Pace', value: formatPace(activity), icon: null },
    { label: 'Average Heart Rate', value: activity.average_heartrate ? `${Math.round(activity.average_heartrate)} bpm` : '--', icon: <Heart className="h-4 w-4" /> },
    { label: 'Max Heart Rate', value: activity.max_heartrate ? `${activity.max_heartrate} bpm` : '--', icon: <Heart className="h-4 w-4" /> },
    { label: 'Elevation Gain', value: activity.elevation_gain_meters ? `${Math.round(activity.elevation_gain_meters)}m` : '--', icon: <Mountain className="h-4 w-4" /> },
    { label: 'Calories', value: activity.calories ? `${Math.round(activity.calories)} cal` : '--', icon: <Flame className="h-4 w-4" /> },
  ];

  function getActivityIcon(type: string | null) {
    return activityIcons[type || 'default'] || activityIcons.default;
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <Card className="w-full max-w-lg max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {getActivityIcon(activity.activity_type)}
            {activity.name || `${activity.activity_type} Activity`}
          </CardTitle>
          <CardDescription>Activity Details</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            {details.map((detail) => (
              <div key={detail.label} className="flex items-center justify-between py-2 border-b last:border-0">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  {detail.icon}
                  {detail.label}
                </div>
                <span className="font-medium">{detail.value}</span>
              </div>
            ))}
          </div>
          <Button onClick={onClose} className="w-full">
            Close
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
