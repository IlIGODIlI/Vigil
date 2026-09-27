import { useState } from 'react';
import { ArrowLeft, ArrowRight, CheckCircle, GitPullRequest, ShieldAlert, Sparkles, X } from 'lucide-react';

interface GuidedTourModalProps {
  onClose: () => void;
}

const STEPS = [
  {
    icon: GitPullRequest,
    title: 'Review what needs attention',
    body: 'Start with pull requests awaiting a human decision. Critical findings are prioritized at the top of your workspace.',
  },
  {
    icon: ShieldAlert,
    title: 'Understand every security finding',
    body: 'Open a finding to review its impact, affected code, and the remediation suggested by Vigil AI.',
  },
  {
    icon: Sparkles,
    title: 'Use Vigil AI in context',
    body: 'Ask Vigil AI to summarize activity, explain a risk, or identify the next item your team should review.',
  },
  {
    icon: CheckCircle,
    title: 'Keep the final decision human',
    body: 'Vigil provides analysis and guidance. Your team still approves, requests changes, or escalates every review.',
  },
];

export default function GuidedTourModal({ onClose }: GuidedTourModalProps) {
  const [step, setStep] = useState(-1);
  const current = step >= 0 ? STEPS[step] : null;
  const StepIcon = current?.icon;

  return (
    <div className="guided-tour-backdrop" role="presentation" onMouseDown={event => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className="guided-tour-modal" role="dialog" aria-modal="true" aria-labelledby="guided-tour-title">
        <button className="guided-tour-close" onClick={onClose} aria-label="Close guided tour">
          <X size={15} />
        </button>

        {current && StepIcon ? (
          <>
            <div className="guided-tour-progress">
              <span>Guided tour</span>
              <span>{step + 1} / {STEPS.length}</span>
            </div>
            <div className="guided-tour-icon"><StepIcon size={19} /></div>
            <h2 id="guided-tour-title">{current.title}</h2>
            <p>{current.body}</p>
            <div className="guided-tour-dots" aria-hidden="true">
              {STEPS.map((_, index) => <i key={index} className={index === step ? 'active' : ''} />)}
            </div>
            <div className="guided-tour-actions">
              <button className="btn btn-secondary btn-sm" onClick={() => step === 0 ? setStep(-1) : setStep(value => value - 1)}>
                <ArrowLeft size={12} /> Back
              </button>
              {step < STEPS.length - 1 ? (
                <button className="btn btn-primary btn-sm" onClick={() => setStep(value => value + 1)}>
                  Next <ArrowRight size={12} />
                </button>
              ) : (
                <button className="btn btn-primary btn-sm" onClick={onClose}>
                  Finish <CheckCircle size={12} />
                </button>
              )}
            </div>
          </>
        ) : (
          <>
            <div className="guided-tour-kicker">Vigil workspace tour</div>
            <h2 id="guided-tour-title">Welcome to Vigil</h2>
            <p>Take a quick guided tour of security reviews, Vigil AI insights, and human approval workflows.</p>
            <div className="guided-tour-actions guided-tour-welcome-actions">
              <button className="btn btn-primary" onClick={() => setStep(0)}>
                Take Guided Tour <ArrowRight size={13} />
              </button>
              <button className="btn btn-ghost" onClick={onClose}>Maybe Later</button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
