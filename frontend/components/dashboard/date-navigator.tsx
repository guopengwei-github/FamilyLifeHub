'use client';

import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import { useState } from 'react';
import { Calendar as CalendarComponent } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';

interface DateNavigatorProps {
  selectedDate: Date;
  onDateChange: (date: Date) => void;
  loading?: boolean;
}

export function DateNavigator({ selectedDate, onDateChange, loading = false }: DateNavigatorProps) {
  const [calendarOpen, setCalendarOpen] = useState(false);

  const goToPreviousDay = () => {
    const newDate = new Date(selectedDate);
    newDate.setDate(newDate.getDate() - 1);
    onDateChange(newDate);
  };

  const goToNextDay = () => {
    const newDate = new Date(selectedDate);
    newDate.setDate(newDate.getDate() + 1);
    onDateChange(newDate);
  };

  const goToToday = () => {
    onDateChange(new Date());
  };

  const handleDateSelect = (date: Date | undefined) => {
    if (date) {
      onDateChange(date);
      setCalendarOpen(false);
    }
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    );
  };

  return (
    <div className="flex items-center justify-center gap-3 py-4 bg-card border-y">
      {/* Previous Day Button */}
      <Button
        variant="outline"
        size="icon"
        onClick={goToPreviousDay}
        disabled={loading}
        className="h-9 w-9"
        aria-label="前一天"
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>

      {/* Date Display with Calendar Popover */}
      <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            disabled={loading}
            className="min-w-[200px] justify-start text-left font-normal"
          >
            <Calendar className="mr-2 h-4 w-4" />
            {format(selectedDate, 'yyyy年M月d日 EEEE', { locale: zhCN })}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="center">
          <CalendarComponent
            mode="single"
            selected={selectedDate}
            onSelect={handleDateSelect}
            initialFocus
          />
        </PopoverContent>
      </Popover>

      {/* Next Day Button */}
      <Button
        variant="outline"
        size="icon"
        onClick={goToNextDay}
        disabled={loading}
        className="h-9 w-9"
        aria-label="后一天"
      >
        <ChevronRight className="h-4 w-4" />
      </Button>

      {/* Today Button */}
      <Button
        variant={isToday(selectedDate) ? "default" : "outline"}
        onClick={goToToday}
        disabled={loading || isToday(selectedDate)}
        className="ml-2"
      >
        今天
      </Button>
    </div>
  );
}
