/**
 * Morning readiness report component.
 */
'use client';

import { useEffect, useState } from 'react';
import { Sunrise } from 'lucide-react';
import { ReportCard } from './report-card';
import { HealthReport } from '@/types/api';
import { getMorningReport } from '@/lib/api';

interface MorningReportProps {
  date?: string;
  onReportGenerated?: (report: HealthReport) => void;
}

export function MorningReport({ date, onReportGenerated }: MorningReportProps) {
  const [report, setReport] = useState<HealthReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getMorningReport(date);
        setReport(data);
      } catch (err: any) {
        if (err.status === 404) {
          setError('今日晨间报告尚未生成');
        } else {
          setError('加载报告失败');
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchReport();
  }, [date]);

  const handleReportGenerated = (newReport: HealthReport) => {
    setReport(newReport);
    setError(null);  // 清除错误状态，确保显示新报告
    onReportGenerated?.(newReport);
  };

  return (
    <ReportCard
      report={report}
      reportType="morning"
      title="晨间精力报告"
      icon={<Sunrise className="h-4 w-4 text-orange-500" />}
      isLoading={isLoading}
      error={error}
      onReportGenerated={handleReportGenerated}
    />
  );
}
