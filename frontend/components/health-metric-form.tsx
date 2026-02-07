'use client';

import { useState } from 'react';
import { type HealthMetricForm as HealthMetricFormType } from '@/types/api';
import { Calendar, Save, X } from 'lucide-react';

interface HealthMetricFormProps {
  initialData?: HealthMetricFormType;
  onSubmit: (data: HealthMetricFormType) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  isSubmitting?: boolean;
}

export function HealthMetricForm({
  initialData,
  onSubmit,
  onCancel,
  submitLabel = 'Save',
  isSubmitting = false,
}: HealthMetricFormProps) {
  const [formData, setFormData] = useState<HealthMetricFormType>(
    initialData || {
      date: new Date().toISOString().split('T')[0],
    }
  );
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = <K extends keyof HealthMetricFormType>(
    field: K,
    value: HealthMetricFormType[K]
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field as string]: '' }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    const newErrors: Record<string, string> = {};

    if (!formData.date) {
      newErrors.date = 'Date is required';
    }
    if (formData.sleep_hours !== undefined && (formData.sleep_hours < 0 || formData.sleep_hours > 24)) {
      newErrors.sleep_hours = 'Sleep hours must be between 0 and 24';
    }
    if (formData.resting_heart_rate !== undefined && (formData.resting_heart_rate < 30 || formData.resting_heart_rate > 200)) {
      newErrors.resting_heart_rate = 'Heart rate must be between 30 and 200';
    }
    if (formData.stress_level !== undefined && (formData.stress_level < 0 || formData.stress_level > 100)) {
      newErrors.stress_level = 'Stress level must be between 0 and 100';
    }
    if (formData.exercise_minutes !== undefined && formData.exercise_minutes < 0) {
      newErrors.exercise_minutes = 'Exercise minutes must be positive';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    await onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Date */}
      <div className="space-y-2">
        <label htmlFor="date" className="text-sm font-medium">
          Date
        </label>
        <div className="relative">
          <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            id="date"
            type="date"
            value={formData.date}
            onChange={(e) => handleChange('date', e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        {errors.date && <p className="text-sm text-red-500">{errors.date}</p>}
      </div>

      {/* Sleep Hours */}
      <div className="space-y-2">
        <label htmlFor="sleep_hours" className="text-sm font-medium">
          Sleep Hours (0-24)
        </label>
        <input
          id="sleep_hours"
          type="number"
          step="0.5"
          min="0"
          max="24"
          value={formData.sleep_hours ?? ''}
          onChange={(e) =>
            handleChange(
              'sleep_hours',
              e.target.value ? parseFloat(e.target.value) : undefined
            )
          }
          placeholder="e.g., 7.5"
          className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {errors.sleep_hours && (
          <p className="text-sm text-red-500">{errors.sleep_hours}</p>
        )}
      </div>

      {/* Resting Heart Rate */}
      <div className="space-y-2">
        <label htmlFor="resting_heart_rate" className="text-sm font-medium">
          Resting Heart Rate (BPM)
        </label>
        <input
          id="resting_heart_rate"
          type="number"
          min="30"
          max="200"
          value={formData.resting_heart_rate ?? ''}
          onChange={(e) =>
            handleChange(
              'resting_heart_rate',
              e.target.value ? parseInt(e.target.value) : undefined
            )
          }
          placeholder="e.g., 65"
          className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {errors.resting_heart_rate && (
          <p className="text-sm text-red-500">{errors.resting_heart_rate}</p>
        )}
      </div>

      {/* Stress Level */}
      <div className="space-y-2">
        <label htmlFor="stress_level" className="text-sm font-medium">
          Stress Level (0-100)
        </label>
        <input
          id="stress_level"
          type="number"
          min="0"
          max="100"
          value={formData.stress_level ?? ''}
          onChange={(e) =>
            handleChange(
              'stress_level',
              e.target.value ? parseInt(e.target.value) : undefined
            )
          }
          placeholder="e.g., 45"
          className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {errors.stress_level && (
          <p className="text-sm text-red-500">{errors.stress_level}</p>
        )}
      </div>

      {/* Exercise Minutes */}
      <div className="space-y-2">
        <label htmlFor="exercise_minutes" className="text-sm font-medium">
          Exercise Minutes
        </label>
        <input
          id="exercise_minutes"
          type="number"
          min="0"
          value={formData.exercise_minutes ?? ''}
          onChange={(e) =>
            handleChange(
              'exercise_minutes',
              e.target.value ? parseInt(e.target.value) : undefined
            )
          }
          placeholder="e.g., 30"
          className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {errors.exercise_minutes && (
          <p className="text-sm text-red-500">{errors.exercise_minutes}</p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          disabled={isSubmitting}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Save className="h-4 w-4" />
          {submitLabel}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="flex items-center justify-center gap-2 px-4 py-2 border rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X className="h-4 w-4" />
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
