import React, { useState } from 'react';
import { Send, AlertTriangle, CheckCircle, Info, X } from 'lucide-react';
import type { ReviewRead } from '../../types';
import { Button } from '../common/Button';
import { reviewService } from '../../services/reviewService';
import { cn } from '../../lib/utils';

interface PublishModalProps {
  review: ReviewRead;
  onClose: () => void;
  onPublished: (updatedReview: ReviewRead) => void;
}

type PublishPhase = 'confirm' | 'publishing' | 'success' | 'error';

export const PublishModal: React.FC<PublishModalProps> = ({ review, onClose, onPublished }) => {
  const [phase, setPhase] = useState<PublishPhase>('confirm');
  const [resultMessage, setResultMessage] = useState('');
  const [resultStatus, setResultStatus] = useState(0);

  const handlePublish = async () => {
    setPhase('publishing');
    const result = await reviewService.publishReview(review.id);
    setResultMessage(result.message);
    setResultStatus(result.status);

    if (result.success) {
      setPhase('success');
      onPublished({ ...review, status: 'PUBLISHED', published_at: new Date().toISOString() });
    } else {
      setPhase('error');
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50"
        onClick={phase !== 'publishing' ? onClose : undefined}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="publish-modal-title"
      >
        <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl shadow-black/50 w-full max-w-md overflow-hidden">
          {/* Header */}
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={cn(
                'w-8 h-8 rounded-lg flex items-center justify-center border',
                phase === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : phase === 'error'
                  ? 'bg-red-500/10 border-red-500/30 text-red-400'
                  : 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
              )}>
                {phase === 'success' ? <CheckCircle className="w-4 h-4" /> :
                 phase === 'error' ? <AlertTriangle className="w-4 h-4" /> :
                 <Send className="w-4 h-4" />}
              </div>
              <h3 id="publish-modal-title" className="text-sm font-semibold text-slate-100">
                {phase === 'success' ? 'Review Published' :
                 phase === 'error' ? 'Publish Failed' :
                 'Publish Review'}
              </h3>
            </div>
            {phase !== 'publishing' && (
              <button
                onClick={onClose}
                className="text-slate-500 hover:text-slate-300 transition-colors rounded-md p-1 hover:bg-slate-800"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Body */}
          <div className="p-5 space-y-4">
            {phase === 'confirm' && (
              <>
                <div className="p-3 bg-amber-950/20 border border-amber-900/30 rounded-lg flex items-start gap-2">
                  <Info className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                  <div className="text-xs text-amber-200/90 space-y-1">
                    <p className="font-medium">You are about to publish this review to GitHub.</p>
                    <p className="text-amber-200/70">This action will post the SecurePR AI review as an official GitHub pull request review. This cannot be undone.</p>
                  </div>
                </div>

                {/* Review summary snippet */}
                {review.summary && (
                  <div>
                    <p className="text-[11px] text-slate-500 uppercase tracking-wider font-medium mb-1.5">Review Summary</p>
                    <p className="text-xs text-slate-300 leading-relaxed p-3 bg-slate-950/60 border border-slate-800/60 rounded-lg line-clamp-3">
                      {review.summary}
                    </p>
                  </div>
                )}

                <div className="flex gap-2 pt-1">
                  <Button variant="outline" size="sm" onClick={onClose} className="flex-1">
                    Cancel
                  </Button>
                  <Button variant="primary" size="sm" onClick={handlePublish} className="flex-1 gap-2">
                    <Send className="w-3.5 h-3.5" />
                    Confirm Publish
                  </Button>
                </div>
              </>
            )}

            {phase === 'publishing' && (
              <div className="py-4 text-center space-y-3">
                <div className="flex items-center justify-center">
                  <div className="w-10 h-10 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin" />
                </div>
                <p className="text-sm text-slate-300">Publishing review to GitHub…</p>
                <p className="text-xs text-slate-500">Please wait while SecurePR submits the review</p>
              </div>
            )}

            {phase === 'success' && (
              <>
                <div className="py-2 text-center space-y-2">
                  <div className="flex items-center justify-center">
                    <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
                      <CheckCircle className="w-6 h-6 text-emerald-400" />
                    </div>
                  </div>
                  <p className="text-sm font-semibold text-emerald-300">Review published successfully</p>
                  <p className="text-xs text-slate-400">{resultMessage}</p>
                </div>
                <Button variant="secondary" size="sm" onClick={onClose} className="w-full">
                  Close
                </Button>
              </>
            )}

            {phase === 'error' && (
              <>
                <div className={cn(
                  'p-3 border rounded-lg',
                  resultStatus === 501
                    ? 'bg-amber-950/20 border-amber-900/30'
                    : 'bg-red-950/20 border-red-900/30'
                )}>
                  <div className="flex items-start gap-2">
                    <AlertTriangle className={cn(
                      'w-4 h-4 mt-0.5 shrink-0',
                      resultStatus === 501 ? 'text-amber-400' : 'text-red-400'
                    )} />
                    <div>
                      <p className={cn(
                        'text-xs font-semibold mb-1',
                        resultStatus === 501 ? 'text-amber-300' : 'text-red-300'
                      )}>
                        {resultStatus === 501
                          ? 'Feature Not Yet Available (Phase 4)'
                          : `Error ${resultStatus || ''}`}
                      </p>
                      <p className="text-xs text-slate-300 leading-relaxed">{resultMessage}</p>
                    </div>
                  </div>
                </div>
                <Button variant="secondary" size="sm" onClick={onClose} className="w-full">
                  Close
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
};
