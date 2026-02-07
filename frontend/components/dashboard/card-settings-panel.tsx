'use client';

import { useEffect, useState } from 'react';
import { X, Check } from 'lucide-react';
import { CardId, CARD_IDS } from '@/types/api';
import { cn } from '@/lib/utils';

interface CardSettingsPanelProps {
  isOpen: boolean;
  hiddenCards: Set<string>;
  onClose: () => void;
  onToggleCard: (cardId: CardId, hidden: boolean) => void;
  className?: string;
}

const CARD_LABELS: Record<CardId, { name: string; icon: string }> = {
  [CARD_IDS.SLEEP]: { name: '睡眠分析', icon: '😴' },
  [CARD_IDS.ACTIVITY_HEALTH]: { name: '运动与健康', icon: '💪' },
  [CARD_IDS.WORK]: { name: '工作数据', icon: '💼' },
  [CARD_IDS.STRESS]: { name: '压力水平', icon: '❤️' },
  [CARD_IDS.TRENDS]: { name: '趋势图表', icon: '📈' },
};

interface CardToggleProps {
  cardId: CardId;
  label: { name: string; icon: string };
  isHidden: boolean;
  onToggle: () => void;
}

function CardToggle({ cardId, label, isHidden, onToggle }: CardToggleProps) {
  return (
    <button
      onClick={onToggle}
      className={cn(
        'w-full flex items-center justify-between p-4 rounded-lg border-2 transition-all',
        'hover:border-primary/50 hover:bg-muted/50',
        isHidden ? 'border-muted opacity-60' : 'border-primary bg-primary/5'
      )}
    >
      <div className="flex items-center gap-3">
        <span className="text-2xl">{label.icon}</span>
        <span className="font-medium">{label.name}</span>
      </div>
      <div
        className={cn(
          'w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all',
          isHidden
            ? 'border-muted bg-background'
            : 'border-primary bg-primary'
        )}
      >
        {!isHidden && <Check className="h-4 w-4 text-primary-foreground" />}
      </div>
    </button>
  );
}

export function CardSettingsPanel({
  isOpen,
  hiddenCards,
  onClose,
  onToggleCard,
  className = '',
}: CardSettingsPanelProps) {
  const [localHiddenCards, setLocalHiddenCards] = useState<Set<string>>(new Set(hiddenCards));

  // Sync local state with props when panel opens
  useEffect(() => {
    if (isOpen) {
      setLocalHiddenCards(new Set(hiddenCards));
    }
  }, [isOpen, hiddenCards]);

  // Close on ESC key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  const handleToggle = (cardId: CardId) => {
    const isHidden = localHiddenCards.has(cardId);
    const newSet = new Set(localHiddenCards);
    if (isHidden) {
      newSet.delete(cardId);
    } else {
      newSet.add(cardId);
    }
    setLocalHiddenCards(newSet);
  };

  const handleComplete = () => {
    // Apply all changes at once
    localHiddenCards.forEach((cardId) => {
      if (!hiddenCards.has(cardId)) {
        onToggleCard(cardId as CardId, true);
      }
    });
    hiddenCards.forEach((cardId) => {
      if (!localHiddenCards.has(cardId)) {
        onToggleCard(cardId as CardId, false);
      }
    });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal Content */}
      <div
        className={cn(
          'relative bg-background rounded-lg shadow-lg max-w-md w-full max-h-[90vh] overflow-auto',
          className
        )}
      >
        {/* Header */}
        <div className="sticky top-0 bg-background border-b p-6 flex items-center justify-between z-10">
          <h2 className="text-xl font-bold">显示设置</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-md hover:bg-muted transition-colors"
            aria-label="关闭"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <p className="text-sm text-muted-foreground mb-4">
            选择要在看板上显示的卡片
          </p>

          <div className="space-y-3">
            {Object.values(CARD_IDS).map((cardId) => (
              <CardToggle
                key={cardId}
                cardId={cardId}
                label={CARD_LABELS[cardId]}
                isHidden={localHiddenCards.has(cardId)}
                onToggle={() => handleToggle(cardId)}
              />
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-background border-t p-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 border rounded-md hover:bg-muted transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleComplete}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  );
}
