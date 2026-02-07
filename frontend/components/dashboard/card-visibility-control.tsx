'use client';

import { Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';

interface CardVisibilityControlProps {
  cardId: string;
  isHidden: boolean;
  onToggle: (cardId: string, hidden: boolean) => void;
  className?: string;
}

export function CardVisibilityControl({
  cardId,
  isHidden,
  onToggle,
  className = ''
}: CardVisibilityControlProps) {
  const [isAnimating, setIsAnimating] = useState(false);

  const handleToggle = () => {
    setIsAnimating(true);
    onToggle(cardId, !isHidden);
    setTimeout(() => setIsAnimating(false), 300);
  };

  return (
    <button
      onClick={handleToggle}
      className={`p-2 rounded-md hover:bg-muted transition-colors ${className}`}
      title={isHidden ? 'Show card' : 'Hide card'}
      aria-label={isHidden ? 'Show card' : 'Hide card'}
    >
      {isHidden ? (
        <EyeOff className="h-4 w-4 text-muted-foreground" />
      ) : (
        <Eye className="h-4 w-4" />
      )}
    </button>
  );
}
