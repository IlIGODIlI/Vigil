import React from 'react';
import { FileText, Calendar, Hash, CheckCircle, Clock, AlertTriangle, Send } from 'lucide-react';
import type { ReviewRead } from '../../types';
import { Card, CardContent, CardHeader, CardTitle } from '../common/Card';
import { Badge } from '../common/Badge';

interface ReviewPreviewProps {
  review: ReviewRead;
}

function getStatusConfig(status: string): {
  label: string;
  variant: 'success' | 'info' | 'secondary' | 'critical' | 'outline';
  icon: React.ReactNode;
} {
  switch (status.toUpperCase()) {
    case 'PUBLISHED':
      return { label: 'Published', variant: 'success', icon: <CheckCircle className="w-3.5 h-3.5" /> };
    case 'READY':
      return { label: 'Ready to Publish', variant: 'info', icon: <Send className="w-3.5 h-3.5" /> };
    case 'DRAFT':
      return { label: 'Draft', variant: 'secondary', icon: <Clock className="w-3.5 h-3.5" /> };
    case 'PUBLISH_FAILED':
      return { label: 'Publish Failed', variant: 'critical', icon: <AlertTriangle className="w-3.5 h-3.5" /> };
    default:
      return { label: status, variant: 'outline', icon: null };
  }
}

export const ReviewPreview: React.FC<ReviewPreviewProps> = ({ review }) => {
  const statusConfig = getStatusConfig(review.status);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-slate-400" />
            <CardTitle>SecurePR AI Review</CardTitle>
          </div>
          <Badge variant={statusConfig.variant} className="gap-1.5">
            {statusConfig.icon}
            {statusConfig.label}
          </Badge>
        </div>

        {/* Meta */}
        <div className="flex items-center gap-4 mt-3 flex-wrap text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <Hash className="w-3 h-3" />
            <span className="font-mono">{review.id.slice(0, 12)}…</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Calendar className="w-3 h-3" />
            Generated: {new Date(review.created_at).toLocaleString()}
          </div>
          {review.published_at && (
            <div className="flex items-center gap-1.5 text-emerald-400">
              <CheckCircle className="w-3 h-3" />
              Published: {new Date(review.published_at).toLocaleString()}
            </div>
          )}
          {review.github_review_id && (
            <div className="flex items-center gap-1.5">
              <span>GitHub Review ID: {review.github_review_id}</span>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Summary */}
        {review.summary && (
          <div>
            <p className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Summary</p>
            <div className="p-3 bg-slate-950/60 border border-slate-800/60 rounded-lg">
              <p className="text-sm text-slate-200 leading-relaxed">{review.summary}</p>
            </div>
          </div>
        )}

        {/* Review body */}
        {review.review_body && (
          <div>
            <p className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Full Review</p>
            <div className="p-4 bg-slate-950/40 border border-slate-800/60 rounded-lg space-y-2">
              {review.review_body.split('\n').map((line, i) => {
                if (line.startsWith('###')) {
                  return (
                    <p key={i} className="text-sm font-semibold text-slate-100 pt-1">
                      {line.replace(/^#+\s*/, '')}
                    </p>
                  );
                }
                if (line.startsWith('##')) {
                  return (
                    <p key={i} className="text-base font-bold text-slate-100 pt-2">
                      {line.replace(/^#+\s*/, '')}
                    </p>
                  );
                }
                if (line.startsWith('- **') || line.startsWith('**')) {
                  return (
                    <p key={i} className="text-xs text-slate-300 pl-2 leading-relaxed">
                      {line.replace(/\*\*/g, '')}
                    </p>
                  );
                }
                if (line.startsWith('- ')) {
                  return (
                    <p key={i} className="text-xs text-slate-400 pl-3 leading-relaxed before:content-['•'] before:mr-2 before:text-slate-600">
                      {line.replace(/^-\s+/, '')}
                    </p>
                  );
                }
                if (line.trim() === '') {
                  return <div key={i} className="h-1" />;
                }
                return (
                  <p key={i} className="text-xs text-slate-300 leading-relaxed">
                    {line}
                  </p>
                );
              })}
            </div>
          </div>
        )}

        {/* No content fallback */}
        {!review.summary && !review.review_body && (
          <div className="py-8 text-center">
            <p className="text-sm text-slate-400">Review data is available but no summary or body content has been generated yet.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
