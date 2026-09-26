import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { Button } from './Button';
import { cn } from '../../lib/utils';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  errorDetail?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Failed to load data',
  message = 'An error occurred while communicating with the backend service.',
  errorDetail,
  onRetry,
  className,
}) => {
  return (
    <div
      className={cn(
        'p-6 bg-red-950/20 border border-red-900/40 rounded-xl text-center flex flex-col items-center justify-center my-4',
        className,
      )}
    >
      <div className="w-10 h-10 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-3 text-red-400">
        <AlertTriangle className="w-5 h-5" />
      </div>
      <h4 className="text-sm font-semibold text-red-300">{title}</h4>
      <p className="text-xs text-red-200/80 mt-1 max-w-md">{message}</p>
      {errorDetail && (
        <pre className="mt-3 p-2.5 bg-slate-950/80 border border-red-900/30 rounded-lg text-xs font-mono text-red-300/90 text-left max-w-lg overflow-x-auto whitespace-pre-wrap">
          {errorDetail}
        </pre>
      )}
      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          icon={<RotateCcw className="w-3.5 h-3.5" />}
          className="mt-4 border-red-800/50 hover:bg-red-950/40 text-red-200"
        >
          Try Again
        </Button>
      )}
    </div>
  );
};
