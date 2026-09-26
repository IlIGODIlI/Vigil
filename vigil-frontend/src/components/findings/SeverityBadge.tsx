import React from 'react';
import type { FindingSeverity } from '../../types';
import { Badge } from '../common/Badge';
import type { BadgeProps } from '../common/Badge';

interface SeverityBadgeProps {
  severity: string;
  className?: string;
}

function getSeverityVariant(severity: string): BadgeProps['variant'] {
  switch (severity.toUpperCase() as FindingSeverity) {
    case 'CRITICAL': return 'critical';
    case 'HIGH':     return 'high';
    case 'MEDIUM':   return 'medium';
    case 'LOW':      return 'low';
    case 'INFO':     return 'info';
    default:         return 'outline';
  }
}

function getSeverityDot(severity: string): string {
  switch (severity.toUpperCase()) {
    case 'CRITICAL': return '●';
    case 'HIGH':     return '●';
    case 'MEDIUM':   return '●';
    case 'LOW':      return '●';
    case 'INFO':     return '○';
    default:         return '○';
  }
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity, className }) => {
  const variant = getSeverityVariant(severity);
  const dot = getSeverityDot(severity);
  return (
    <Badge variant={variant} className={className}>
      <span className="text-[10px]">{dot}</span>
      {severity.toUpperCase()}
    </Badge>
  );
};
