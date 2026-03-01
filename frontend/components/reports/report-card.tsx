/**
 * Generic report card component for displaying health reports.
 */
'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { HealthReport } from '@/types/api';
import { regenerateReport } from '@/lib/api';

interface ReportCardProps {
  report: HealthReport | null;
  reportType: 'morning' | 'evening';
  title: string;
  icon: React.ReactNode;
  isLoading?: boolean;
  error?: string | null;
  onReportGenerated?: (report: HealthReport) => void;
}

export function ReportCard({
  report,
  reportType,
  title,
  icon,
  isLoading,
  error,
  onReportGenerated,
}: ReportCardProps) {
  const [isRegenerating, setIsRegenerating] = useState(false);

  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      const newReport = await regenerateReport(reportType);
      onReportGenerated?.(newReport);
    } catch (err) {
      console.error('Failed to regenerate report:', err);
    } finally {
      setIsRegenerating(false);
    }
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          {icon}
          {title}
        </CardTitle>
        {report && (
          <span className="text-xs text-muted-foreground">
            {formatTime(report.generated_at)}
          </span>
        )}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : error ? (
          <div className="text-center py-4">
            <p className="text-sm text-muted-foreground mb-2">{error}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRegenerate}
              disabled={isRegenerating}
            >
              {isRegenerating ? '生成中...' : '生成报告'}
            </Button>
          </div>
        ) : report ? (
          <div className="space-y-2">
            <div className="prose prose-sm dark:prose-invert max-w-none text-sm">
              <div
                className="report-content"
                dangerouslySetInnerHTML={{ __html: formatMarkdown(report.content) }}
              />
            </div>
            <div className="flex justify-end pt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRegenerate}
                disabled={isRegenerating}
                className="text-xs"
              >
                {isRegenerating ? '重新生成中...' : '重新生成'}
              </Button>
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            <p className="text-sm text-muted-foreground mb-2">暂无报告</p>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRegenerate}
              disabled={isRegenerating}
            >
              {isRegenerating ? '生成中...' : '生成报告'}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Simple markdown to HTML converter for basic formatting.
 */
function formatMarkdown(content: string): string {
  return content
    // Headers
    .replace(/^### (.*$)/gim, '<h4 class="font-semibold text-base mt-3 mb-1">$1</h4>')
    .replace(/^## (.*$)/gim, '<h3 class="font-bold text-lg mt-4 mb-2">$1</h3>')
    // Bold
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // List items
    .replace(/^- (.*$)/gim, '<li class="ml-4">$1</li>')
    // Line breaks
    .replace(/\n/g, '<br/>');
}
