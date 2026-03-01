/**
 * Evening review report component.
 */
'use client';

import { useEffect, useState } from 'react';
import { Moon } from 'lucide-react';
import { ReportCard } from './report-card';
import { HealthReport } from '@/types/api';
import { getEveningReport } from '@/lib/api';

interface EveningReportProps {
  date?: string;
  onReportGenerated?: (report: HealthReport) => void;
}

export function EveningReport({ date, onReportGenerated }: EveningReportProps) {
  const [report, setReport] = useState<HealthReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getEveningReport(date);
        setReport(data);
      } catch (err: any) {
        if (err.status === 404) {
          setError('今日晚间报告尚未生成');
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
    onReportGenerated?.(newReport);
  };

  return (
    <ReportCard
      report={report}
      reportType="evening"
      title="晚间复盘报告"
      icon={<Moon className="h-4 w-4 text-indigo-500" />}
      isLoading={isLoading}
      error={error}
      onReportGenerated={handleReportGenerated}
    />
  );
}
