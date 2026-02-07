'use client';

import { useEffect, useState } from 'react';
import { ProtectedRoute } from '@/components/protected-route';
import { SiteHeader } from '@/components/site-header';
import { HealthMetricForm } from '@/components/health-metric-form';
import { HealthMetric, type HealthMetricForm as HealthMetricFormType } from '@/types/api';
import {
  listHealthMetrics,
  createHealthMetric,
  updateHealthMetric,
  deleteHealthMetric,
} from '@/lib/api';
import {
  Plus,
  Calendar,
  Moon,
  Heart,
  Activity,
  Dumbbell,
  Trash2,
  Edit2,
  RefreshCw,
} from 'lucide-react';

export default function HealthPage() {
  const [metrics, setMetrics] = useState<HealthMetric[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingMetric, setEditingMetric] = useState<HealthMetric | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listHealthMetrics();
      setMetrics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health metrics');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const handleSubmit = async (data: HealthMetricFormType) => {
    setIsSubmitting(true);
    setError(null);
    try {
      if (editingMetric) {
        await updateHealthMetric(editingMetric.date, data);
      } else {
        await createHealthMetric(data);
      }
      await fetchMetrics();
      setShowForm(false);
      setEditingMetric(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save health metric');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEdit = (metric: HealthMetric) => {
    setEditingMetric(metric);
    setShowForm(true);
  };

  const handleDelete = async (date: string) => {
    if (!confirm('Are you sure you want to delete this health metric?')) {
      return;
    }
    setError(null);
    try {
      await deleteHealthMetric(date);
      await fetchMetrics();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete health metric');
    }
  };

  const handleCancelForm = () => {
    setShowForm(false);
    setEditingMetric(null);
  };

  const handleAddNew = () => {
    setEditingMetric(null);
    setShowForm(true);
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen">
        <SiteHeader />
        <main className="container mx-auto px-4 py-8">
          <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold tracking-tight">Health Data</h1>
                <p className="text-muted-foreground">
                  Manage and track your health metrics manually
                </p>
              </div>
              <button
                onClick={handleAddNew}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                <Plus className="h-4 w-4" />
                Add Metric
              </button>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-md text-destructive">
                {error}
              </div>
            )}

            {/* Form Modal */}
            {showForm && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-card rounded-xl p-6 w-full max-w-md shadow-lg">
                  <h2 className="text-xl font-bold mb-4">
                    {editingMetric ? 'Edit Health Metric' : 'Add Health Metric'}
                  </h2>
                  <HealthMetricForm
                    initialData={
                      editingMetric
                        ? {
                            date: editingMetric.date,
                            sleep_hours: editingMetric.sleep_hours ?? undefined,
                            resting_heart_rate: editingMetric.resting_heart_rate ?? undefined,
                            stress_level: editingMetric.stress_level ?? undefined,
                            exercise_minutes: editingMetric.exercise_minutes ?? undefined,
                          }
                        : undefined
                    }
                    onSubmit={handleSubmit}
                    onCancel={handleCancelForm}
                    submitLabel={editingMetric ? 'Update' : 'Save'}
                    isSubmitting={isSubmitting}
                  />
                </div>
              </div>
            )}

            {/* Metrics List */}
            {isLoading ? (
              <div className="flex justify-center py-8">
                <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : metrics.length === 0 ? (
              <div className="text-center py-12">
                <Activity className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">No health metrics yet</h3>
                <p className="text-muted-foreground mb-4">
                  Start tracking your health by adding your first metric
                </p>
                <button
                  onClick={handleAddNew}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
                >
                  <Plus className="h-4 w-4" />
                  Add First Metric
                </button>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {metrics.map((metric) => (
                  <div
                    key={metric.id}
                    className="border rounded-lg p-4 hover:border-primary/50 transition-colors"
                  >
                    {/* Date Header */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Calendar className="h-4 w-4" />
                        {metric.date}
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleEdit(metric)}
                          className="p-1.5 hover:bg-muted rounded-md transition-colors"
                          title="Edit"
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(metric.date)}
                          className="p-1.5 hover:bg-destructive/10 hover:text-destructive rounded-md transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    {/* Metrics Grid */}
                    <div className="grid grid-cols-2 gap-3">
                      {metric.sleep_hours !== null && (
                        <div className="flex items-center gap-2">
                          <Moon className="h-4 w-4 text-blue-500" />
                          <div>
                            <p className="text-xs text-muted-foreground">Sleep</p>
                            <p className="font-medium">{metric.sleep_hours}h</p>
                          </div>
                        </div>
                      )}
                      {metric.resting_heart_rate !== null && (
                        <div className="flex items-center gap-2">
                          <Heart className="h-4 w-4 text-red-500" />
                          <div>
                            <p className="text-xs text-muted-foreground">Heart Rate</p>
                            <p className="font-medium">{metric.resting_heart_rate} bpm</p>
                          </div>
                        </div>
                      )}
                      {metric.stress_level !== null && (
                        <div className="flex items-center gap-2">
                          <Activity className="h-4 w-4 text-orange-500" />
                          <div>
                            <p className="text-xs text-muted-foreground">Stress</p>
                            <p className="font-medium">{metric.stress_level}/100</p>
                          </div>
                        </div>
                      )}
                      {metric.exercise_minutes !== null && (
                        <div className="flex items-center gap-2">
                          <Dumbbell className="h-4 w-4 text-green-500" />
                          <div>
                            <p className="text-xs text-muted-foreground">Exercise</p>
                            <p className="font-medium">{metric.exercise_minutes} min</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
