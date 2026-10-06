import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { ArrowUp, ShieldCheck, Sparkles, X } from 'lucide-react';
import { useApp, type Lang } from '../contexts/AppContext';
import darkBotImage from '../imports/dbot.png';
import lightBotImage from '../imports/lbot.png';
import darkBotButtonImage from '../imports/dbot-2.png';
import lightBotButtonImage from '../imports/lbot-2.png';

interface AssistantContext {
  hint: Record<Lang, string>;
  body: Record<Lang, string>;
  suggestions: Record<Lang, string[]>;
}

const CONTEXT: Record<string, AssistantContext> = {
  '/dashboard': {
    hint: {
      en: 'Security workspace overview',
      hi: 'सुरक्षा वर्कस्पेस का सारांश',
      hinglish: 'Security workspace ka overview',
    },
    body: {
      en: '3 pull requests need a human decision. PR #47 has 2 critical findings, with JWT secret exposure as the highest priority.',
      hi: '3 पुल रिक्वेस्ट पर मानवीय निर्णय आवश्यक है। PR #47 में 2 गंभीर समस्याएँ हैं, जिनमें JWT सीक्रेट सबसे महत्वपूर्ण है।',
      hinglish: '3 Pull Requests ko human decision chahiye. PR #47 mein 2 critical findings hain; JWT secret exposure sabse high priority hai.',
    },
    suggestions: {
      en: ['What needs my attention?', 'Show critical findings', 'Summarize today’s security activity'],
      hi: ['मुझे किस पर ध्यान देना चाहिए?', 'गंभीर समस्याएँ दिखाएँ', 'आज की सुरक्षा गतिविधि का सारांश दें'],
      hinglish: ['Mujhe kis par attention dena chahiye?', 'Critical findings dikhao', 'Aaj ki security activity summarize karo'],
    },
  },
  '/pull-requests': {
    hint: { en: 'Pull Request review context', hi: 'पुल रिक्वेस्ट समीक्षा संदर्भ', hinglish: 'Pull Request review context' },
    body: {
      en: 'PR #47 introduces a hardcoded JWT secret that could allow token forgery. AI review is complete, but the human decision is still pending.',
      hi: 'PR #47 में हार्डकोडेड JWT सीक्रेट है जिससे टोकन जालसाजी हो सकती है। AI समीक्षा पूरी है, लेकिन मानवीय निर्णय लंबित है।',
      hinglish: 'PR #47 mein hardcoded JWT secret hai jo token forgery allow kar sakta hai. AI review complete hai, lekin human decision pending hai.',
    },
    suggestions: {
      en: ['Why was this PR flagged?', 'Which files are affected?', 'Explain the highest-risk finding'],
      hi: ['इस PR को क्यों चिह्नित किया गया?', 'कौन-सी फाइलें प्रभावित हैं?', 'सबसे गंभीर समस्या समझाएँ'],
      hinglish: ['Yeh PR flag kyun hua?', 'Kaunsi files affected hain?', 'Highest-risk finding explain karo'],
    },
  },
  '/findings': {
    hint: { en: 'Security finding context', hi: 'सुरक्षा समस्या का संदर्भ', hinglish: 'Security Finding context' },
    body: {
      en: '2 critical findings are open. Hardcoded secrets are the most common pattern and should be remediated before merge.',
      hi: '2 गंभीर समस्याएँ खुली हैं। हार्डकोडेड सीक्रेट सबसे सामान्य पैटर्न है और मर्ज से पहले इसे ठीक करना चाहिए।',
      hinglish: '2 critical findings open hain. Hardcoded secrets sabse common pattern hai; merge se pehle fix karna chahiye.',
    },
    suggestions: {
      en: ['Explain this security finding', 'What is the potential impact?', 'Show the suggested fix'],
      hi: ['यह सुरक्षा समस्या समझाएँ', 'इसका संभावित प्रभाव क्या है?', 'सुझाया गया समाधान दिखाएँ'],
      hinglish: ['Yeh Security Finding explain karo', 'Potential impact kya hai?', 'Suggested fix dikhao'],
    },
  },
};

const DEFAULT_CONTEXT: AssistantContext = {
  hint: { en: 'Context-aware security assistant', hi: 'संदर्भ-आधारित सुरक्षा सहायक', hinglish: 'Context-aware security assistant' },
  body: {
    en: 'I can summarize the security signals on this page and help you decide what to review next.',
    hi: 'मैं इस पेज के सुरक्षा संकेतों का सारांश दे सकता हूँ और अगली समीक्षा चुनने में मदद कर सकता हूँ।',
    hinglish: 'Main is page ke security signals summarize karke next review choose karne mein help kar sakta hoon.',
  },
  suggestions: {
    en: ['What needs my attention?', 'Summarize this page', 'Show the highest risk'],
    hi: ['मुझे किस पर ध्यान देना चाहिए?', 'इस पेज का सारांश दें', 'सबसे बड़ा जोखिम दिखाएँ'],
    hinglish: ['Mujhe kis par attention dena chahiye?', 'Yeh page summarize karo', 'Highest risk dikhao'],
  },
};

export default function FloatingAssistant() {
  const { lang, t, theme } = useApp();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [answer, setAnswer] = useState('');
  const context = CONTEXT[location.pathname] ?? DEFAULT_CONTEXT;

  useEffect(() => {
    setOpen(false);
    setAnswer('');
    setInput('');
  }, [location.pathname]);

  const submitQuestion = (question = input) => {
    if (!question.trim()) return;
    setInput('');
    window.setTimeout(() => setAnswer(context.body[lang]), 180);
  };

  return (
    <>
      {open && (
        <aside className="assistant-panel" aria-label={t('askVigilAI')}>
          <header className="assistant-header">
            <div className="assistant-identity">
              <img className="assistant-bot-image assistant-bot-image-header" src={theme === 'light' ? lightBotImage : darkBotImage} alt="" aria-hidden="true" />
              <div>
                <strong>{t('askVigilAI')}</strong>
                <span><i /> {context.hint[lang]}</span>
              </div>
            </div>
            <button className="assistant-icon-button" onClick={() => setOpen(false)} aria-label={t('close')}>
              <X size={16} />
            </button>
          </header>

          <div className="assistant-content">
            <div className="assistant-context-label"><Sparkles size={12} /> {t('contextualInsight')}</div>
            <div className="assistant-insight">{context.body[lang]}</div>

            <div className="assistant-guidance">
              <ShieldCheck size={14} />
              <div><strong>{t('remediationGuidance')}</strong><span>{t('remediationBody')}</span></div>
            </div>

            <div className="assistant-section-label">{t('suggestedQuestions')}</div>
            <div className="assistant-suggestions">
              {context.suggestions[lang].map(suggestion => (
                <button key={suggestion} onClick={() => { setInput(suggestion); submitQuestion(suggestion); }}>
                  {suggestion}<ArrowUp size={11} />
                </button>
              ))}
            </div>

            {answer && (
              <div className="assistant-answer">
                <span><img className="assistant-bot-image assistant-bot-image-answer" src={theme === 'light' ? lightBotImage : darkBotImage} alt="" aria-hidden="true" /></span>
                <p>{answer}</p>
              </div>
            )}
          </div>

          <div className="assistant-composer">
            <input
              value={input}
              onChange={event => setInput(event.target.value)}
              onKeyDown={event => { if (event.key === 'Enter') submitQuestion(); }}
              placeholder={t('askPlaceholder')}
            />
            <button onClick={() => submitQuestion()} disabled={!input.trim()} aria-label={t('send')}>
              <ArrowUp size={14} />
            </button>
          </div>
          <footer>{t('mockAiNotice')}</footer>
        </aside>
      )}

      <button
        className={`assistant-trigger${open ? ' active' : ''}`}
        onClick={() => setOpen(value => !value)}
        aria-expanded={open}
        aria-label={t('askVigilAI')}
      >
        <img className="assistant-bot-image assistant-bot-image-trigger" src={theme === 'light' ? lightBotButtonImage : darkBotButtonImage} alt="" aria-hidden="true" />
        <span>{t('askVigilAI')}</span>
      </button>
    </>
  );
}
