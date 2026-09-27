import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

export type Theme = 'dark' | 'light';
export type Lang = 'en' | 'hi' | 'hinglish';

type Translation = Record<Lang, string>;

interface AppState {
  theme: Theme;
  lang: Lang;
  githubConnected: boolean;
  aiPanelOpen: boolean;
  setTheme: (theme: Theme) => void;
  setLang: (lang: Lang) => void;
  setGithubConnected: (connected: boolean) => void;
  setAiPanelOpen: (open: boolean) => void;
  t: (key: string) => string;
}

const THEME_KEY = 'vigil.theme';
const LANGUAGE_KEY = 'vigil.language';

const translations: Record<string, Translation> = {
  dashboard: { en: 'Dashboard', hi: 'डैशबोर्ड', hinglish: 'Dashboard' },
  repositories: { en: 'Repositories', hi: 'रिपॉजिटरी', hinglish: 'Repositories' },
  pullRequests: { en: 'Pull Requests', hi: 'पुल रिक्वेस्ट', hinglish: 'Pull Requests' },
  reviewQueue: {
  en: 'Review Queue', hi: 'रिव्यू क्यू', hinglish: 'Review Queue' },
  findings: { en: 'Security Findings', hi: 'सुरक्षा संबंधी समस्याएँ', hinglish: 'Security Findings' },
  commits: { en: 'Commit Analysis', hi: 'कमिट विश्लेषण', hinglish: 'Commit Analysis' },
  analytics: { en: 'Analytics', hi: 'विश्लेषिकी', hinglish: 'Analytics' },
  reviewHistory: { en: 'Review History', hi: 'समीक्षा इतिहास', hinglish: 'Review History' },
  settings: { en: 'Settings', hi: 'सेटिंग्स', hinglish: 'Settings' },
  aiAssistant: { en: 'AI Assistant', hi: 'AI सहायक', hinglish: 'AI Assistant' },
  account: { en: 'Account', hi: 'खाता', hinglish: 'Account' },
  appearance: { en: 'Appearance', hi: 'दिखावट', hinglish: 'Appearance' },
  theme: { en: 'Theme', hi: 'थीम', hinglish: 'Theme' },
  language: { en: 'Language', hi: 'भाषा', hinglish: 'Language' },
  english: { en: 'English', hi: 'अंग्रेज़ी', hinglish: 'English' },
  hindi: { en: 'Hindi', hi: 'हिंदी', hinglish: 'Hindi' },
  hinglish: { en: 'Hinglish', hi: 'हिंग्लिश', hinglish: 'Hinglish' },
  dark: { en: 'Dark', hi: 'डार्क', hinglish: 'Dark' },
  light: { en: 'Light', hi: 'लाइट', hinglish: 'Light' },
  workspacePreferences: {
    en: 'Workspace preferences and integrations',
    hi: 'वर्कस्पेस की प्राथमिकताएँ और एकीकरण',
    hinglish: 'Workspace preferences aur integrations',
  },
  chooseTheme: {
    en: 'Choose your preferred display mode',
    hi: 'अपना पसंदीदा डिस्प्ले मोड चुनें',
    hinglish: 'Apna preferred display mode choose karein',
  },
  chooseLanguage: {
    en: 'Choose the language used across Vigil',
    hi: 'Vigil में उपयोग की जाने वाली भाषा चुनें',
    hinglish: 'Vigil mein use hone wali language choose karein',
  },
  signOut: { en: 'Sign out', hi: 'साइन आउट', hinglish: 'Sign out' },
  giveTour: { en: 'Give a tour', hi: 'टूर दिखाएँ', hinglish: 'Tour dikhayein' },
  localSession: { en: 'Local session', hi: 'स्थानीय सत्र', hinglish: 'Local session' },
  comingSoon: { en: 'Coming soon', hi: 'जल्द आ रहा है', hinglish: 'Coming soon' },
  microsoftAuth: { en: 'Microsoft authentication', hi: 'Microsoft प्रमाणीकरण', hinglish: 'Microsoft authentication' },
  microsoftAuthDescription: {
    en: 'Enterprise authentication with Microsoft Entra ID',
    hi: 'Microsoft Entra ID के साथ एंटरप्राइज़ प्रमाणीकरण',
    hinglish: 'Microsoft Entra ID ke saath enterprise authentication',
  },
  signOutDescription: {
    en: 'End this local Vigil preview session',
    hi: 'यह स्थानीय Vigil पूर्वावलोकन सत्र समाप्त करें',
    hinglish: 'Yeh local Vigil preview session end karein',
  },
  goodMorning: { en: 'Good morning', hi: 'सुप्रभात', hinglish: 'Good morning' },
  aiActive: { en: 'AI active', hi: 'AI सक्रिय है', hinglish: 'AI active hai' },
  attentionMessage: {
    en: '2 critical findings across 2 pull requests need your review.',
    hi: '2 पुल रिक्वेस्ट में 2 गंभीर समस्याओं की समीक्षा आवश्यक है।',
    hinglish: '2 Pull Requests mein 2 critical findings ko aapke review ki zaroorat hai.',
  },
  reviewNow: { en: 'Review now', hi: 'अभी समीक्षा करें', hinglish: 'Abhi review karein' },
  pending: { en: 'pending', hi: 'लंबित', hinglish: 'pending' },
  viewAll: { en: 'View all', hi: 'सभी देखें', hinglish: 'Sab dekhein' },
  vigilAI: { en: 'Vigil AI', hi: 'Vigil AI', hinglish: 'Vigil AI' },
  analysisInProgress: {
    en: '1 analysis in progress',
    hi: '1 विश्लेषण जारी है',
    hinglish: '1 analysis chal raha hai',
  },
  analyzing: { en: 'Analyzing', hi: 'विश्लेषण जारी', hinglish: 'Analyze ho raha hai' },
  remaining: { en: '~2 min remaining', hi: '~2 मिनट शेष', hinglish: '~2 min baaki' },
  openPRs: { en: 'Open PRs', hi: 'खुले PR', hinglish: 'Open PRs' },
  criticalFindings: { en: 'Critical findings', hi: 'गंभीर समस्याएँ', hinglish: 'Critical findings' },
  reviewedToday: { en: 'Reviewed today', hi: 'आज समीक्षा की गई', hinglish: 'Aaj reviewed' },
  averageReviewTime: { en: 'Avg. review time', hi: 'औसत समीक्षा समय', hinglish: 'Avg. review time' },
  needDecision: { en: '3 need decision', hi: '3 पर निर्णय आवश्यक', hinglish: '3 ko decision chahiye' },
  acrossRepos: { en: 'Across 2 repos', hi: '2 रिपॉजिटरी में', hinglish: '2 repos mein' },
  fromYesterday: { en: '+2 from yesterday', hi: 'कल से +2', hinglish: 'Kal se +2' },
  lastSevenDays: { en: 'Last 7 days', hi: 'पिछले 7 दिन', hinglish: 'Pichhle 7 days' },
  recentCommits: { en: 'Recent Commits', hi: 'हाल के कमिट', hinglish: 'Recent Commits' },
  securityPosture: { en: 'Security Posture', hi: 'सुरक्षा स्थिति', hinglish: 'Security Posture' },
  allRepositories: { en: 'All repositories', hi: 'सभी रिपॉजिटरी', hinglish: 'Saari repositories' },
  reviewActivity: { en: 'Review Activity', hi: 'समीक्षा गतिविधि', hinglish: 'Review Activity' },
  approved: { en: 'Approved', hi: 'स्वीकृत', hinglish: 'Approved' },
  changesRequested: { en: 'Changes requested', hi: 'बदलाव आवश्यक', hinglish: 'Changes requested' },
  escalated: { en: 'Escalated', hi: 'आगे भेजा गया', hinglish: 'Escalated' },
  inProgress: { en: 'In progress', hi: 'जारी है', hinglish: 'In progress' },
  githubConnection: { en: 'GitHub Connection', hi: 'GitHub कनेक्शन', hinglish: 'GitHub Connection' },
  aiPreferences: { en: 'AI Preferences', hi: 'AI प्राथमिकताएँ', hinglish: 'AI Preferences' },
  dangerZone: { en: 'Danger Zone', hi: 'सावधानी क्षेत्र', hinglish: 'Danger Zone' },
  connectedOrganization: { en: 'Connected organization', hi: 'जुड़ा हुआ संगठन', hinglish: 'Connected organization' },
  repositoriesAccessible: { en: '6 repositories accessible', hi: '6 रिपॉजिटरी उपलब्ध', hinglish: '6 repositories accessible hain' },
  connected: { en: 'Connected', hi: 'जुड़ा हुआ', hinglish: 'Connected' },
  disconnected: { en: 'Disconnected', hi: 'डिस्कनेक्टेड', hinglish: 'Disconnected' },
  manage: { en: 'Manage', hi: 'प्रबंधित करें', hinglish: 'Manage' },
  analyzedRepositories: { en: 'Analyzed repositories', hi: 'विश्लेषित रिपॉजिटरी', hinglish: 'Analyzed repositories' },
  edit: { en: 'Edit', hi: 'संपादित करें', hinglish: 'Edit' },
  analysisDepth: { en: 'Analysis depth', hi: 'विश्लेषण की गहराई', hinglish: 'Analysis depth' },
  analysisDepthDescription: {
    en: 'Deep mode catches more issues but increases analysis time by ~2×',
    hi: 'डीप मोड अधिक समस्याएँ पहचानता है, लेकिन विश्लेषण में लगभग दोगुना समय लगता है',
    hinglish: 'Deep mode zyada issues detect karta hai, par analysis time ~2× badhta hai',
  },
  standard: { en: 'Standard', hi: 'मानक', hinglish: 'Standard' },
  deep: { en: 'Deep', hi: 'गहन', hinglish: 'Deep' },
  autoAnalyze: { en: 'Auto-analyze on PR open', hi: 'PR खुलने पर स्वतः विश्लेषण', hinglish: 'PR open hote hi auto-analyze' },
  autoAnalyzeDescription: {
    en: 'Begin AI security analysis automatically when a PR is opened',
    hi: 'PR खुलते ही AI सुरक्षा विश्लेषण अपने आप शुरू करें',
    hinglish: 'PR open hote hi AI security analysis automatically start karein',
  },
  findingNotifications: { en: 'Critical finding notifications', hi: 'गंभीर समस्या की सूचनाएँ', hinglish: 'Critical finding notifications' },
  findingNotificationsDescription: {
    en: 'Send an alert when AI detects critical severity findings',
    hi: 'AI द्वारा गंभीर समस्या मिलने पर अलर्ट भेजें',
    hinglish: 'AI ko critical finding mile toh alert bhejein',
  },
  autoEscalate: { en: 'Auto-escalate unreviewed PRs', hi: 'बिना समीक्षा वाले PR को आगे भेजें', hinglish: 'Unreviewed PRs auto-escalate karein' },
  autoEscalateDescription: {
    en: 'Flag PRs that remain unreviewed after 48 hours',
    hi: '48 घंटे तक बिना समीक्षा वाले PR को चिह्नित करें',
    hinglish: '48 hours tak unreviewed PRs ko flag karein',
  },
  disconnectGitHub: { en: 'Disconnect GitHub', hi: 'GitHub डिस्कनेक्ट करें', hinglish: 'GitHub disconnect karein' },
  disconnectGitHubDescription: {
    en: 'Removes Vigil access to all repositories. Analysis stops immediately.',
    hi: 'सभी रिपॉजिटरी से Vigil की पहुँच हटती है और विश्लेषण तुरंत रुक जाता है।',
    hinglish: 'Saari repositories se Vigil access remove hoga aur analysis turant ruk jayega.',
  },
  disconnect: { en: 'Disconnect', hi: 'डिस्कनेक्ट करें', hinglish: 'Disconnect' },
  deleteAccount: { en: 'Delete account', hi: 'खाता हटाएँ', hinglish: 'Account delete karein' },
  deleteAccountDescription: {
    en: 'Permanently delete your Vigil account and all associated data.',
    hi: 'अपना Vigil खाता और उससे जुड़ा सारा डेटा स्थायी रूप से हटाएँ।',
    hinglish: 'Apna Vigil account aur associated data permanently delete karein.',
  },
  delete: { en: 'Delete', hi: 'हटाएँ', hinglish: 'Delete' },
  askVigilAI: { en: 'Ask Vigil AI', hi: 'Vigil AI से पूछें', hinglish: 'Vigil AI se poochhein' },
  contextualInsight: { en: 'Contextual insight', hi: 'संदर्भ आधारित जानकारी', hinglish: 'Contextual insight' },
  remediationGuidance: { en: 'Review guidance', hi: 'समीक्षा मार्गदर्शन', hinglish: 'Review guidance' },
  remediationBody: {
    en: 'Validate the security impact, inspect the affected diff, then make the final human decision.',
    hi: 'सुरक्षा प्रभाव जाँचें, प्रभावित डिफ देखें, फिर अंतिम मानवीय निर्णय लें।',
    hinglish: 'Security impact validate karein, affected diff inspect karein, phir final human decision lein.',
  },
  suggestedQuestions: { en: 'Suggested questions', hi: 'सुझाए गए प्रश्न', hinglish: 'Suggested questions' },
  askPlaceholder: { en: 'Ask about this page…', hi: 'इस पेज के बारे में पूछें…', hinglish: 'Is page ke baare mein poochhein…' },
  mockAiNotice: {
    en: 'Demo responses use the current page context',
    hi: 'डेमो उत्तर वर्तमान पेज के संदर्भ पर आधारित हैं',
    hinglish: 'Demo responses current page context use karte hain',
  },
  close: { en: 'Close', hi: 'बंद करें', hinglish: 'Close' },
  send: { en: 'Send', hi: 'भेजें', hinglish: 'Send' },
  navDashboardContext: {
    en: 'Overview of all repositories, pending reviews, security alerts, and AI analysis status.',
    hi: 'सभी रिपॉजिटरी, लंबित समीक्षाओं, सुरक्षा अलर्ट और AI विश्लेषण की स्थिति का सारांश।',
    hinglish: 'Saari repositories, pending reviews, security alerts aur AI analysis ka overview.',
  },
  navRepositoriesContext: {
    en: 'Browse connected GitHub repositories and monitor their security posture and activity.',
    hi: 'जुड़ी हुई GitHub रिपॉजिटरी और उनकी सुरक्षा स्थिति देखें।',
    hinglish: 'Connected GitHub repositories aur unki security posture monitor karein.',
  },
  navPullRequestsContext: {
    en: 'Open pull requests with AI security analysis, findings summary, and pending human decisions.',
    hi: 'AI सुरक्षा विश्लेषण और लंबित निर्णयों के साथ खुले पुल रिक्वेस्ट।',
    hinglish: 'Open Pull Requests, AI security analysis aur pending human decisions dekhein.',
  },
  navReviewQueueContext: {
  en: 'Review AI-analyzed pull requests that are waiting for your security decision.',
  hi: 'AI द्वारा विश्लेषित उन पुल रिक्वेस्ट्स की समीक्षा करें जो आपके सुरक्षा निर्णय की प्रतीक्षा कर रही हैं।',
  hinglish: 'AI-analyzed pull requests review karein jo aapke security decision ka wait kar rahe hain.',
},
  navFindingsContext: {
    en: 'Security findings ranked by severity, with an AI explanation and suggested fix.',
    hi: 'गंभीरता के अनुसार सुरक्षा समस्याएँ, AI स्पष्टीकरण और सुझाए गए समाधान के साथ।',
    hinglish: 'Severity ke hisaab se Security Findings, AI explanation aur suggested fix ke saath.',
  },
  navCommitsContext: {
    en: 'Inspect commits for secrets, security-sensitive patterns, and dependency changes.',
    hi: 'कमिट में सीक्रेट, सुरक्षा पैटर्न और डिपेंडेंसी बदलाव देखें।',
    hinglish: 'Commits mein secrets, security-sensitive patterns aur dependency changes check karein.',
  },
  navAnalyticsContext: {
    en: 'Security trends, review velocity, finding patterns, and team activity over time.',
    hi: 'समय के साथ सुरक्षा रुझान, समीक्षा गति और टीम गतिविधि।',
    hinglish: 'Security trends, review velocity aur team activity ko time ke saath dekhein.',
  },
  navHistoryContext: {
    en: 'Complete audit trail of past reviews, decisions, findings, and reviewer notes.',
    hi: 'पिछली समीक्षाओं, निर्णयों और टिप्पणियों का पूरा रिकॉर्ड।',
    hinglish: 'Past reviews, decisions, findings aur reviewer notes ka complete audit trail.',
  },
  navAttention: { en: '3 need attention', hi: '3 पर ध्यान आवश्यक', hinglish: '3 ko attention chahiye' },
  navAnalyzed: { en: '4 of 6 analyzed', hi: '6 में से 4 का विश्लेषण', hinglish: '6 mein se 4 analyzed' },
  navPendingReviews: { en: '3 pending review', hi: '3 समीक्षाएँ लंबित', hinglish: '3 reviews pending' },
  navCriticalOpen: { en: '2 critical open', hi: '2 गंभीर समस्याएँ खुली', hinglish: '2 critical open' },
  navFlaggedToday: { en: '3 flagged today', hi: 'आज 3 चिह्नित', hinglish: 'Aaj 3 flagged' },
  navUpdatedNow: { en: 'Updated now', hi: 'अभी अपडेट किया गया', hinglish: 'Abhi updated' },
  navReviewsMonth: { en: '28 this month', hi: 'इस महीने 28', hinglish: 'Is month 28' },
};

const AppContext = createContext<AppState | null>(null);

function initialTheme(): Theme {
  const stored = window.localStorage.getItem(THEME_KEY);
  return stored === 'light' ? 'light' : 'dark';
}

function initialLanguage(): Lang {
  const stored = window.localStorage.getItem(LANGUAGE_KEY);
  return stored === 'hi' || stored === 'hinglish' ? stored : 'en';
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [lang, setLang] = useState<Lang>(initialLanguage);
  const [githubConnected, setGithubConnected] = useState(true);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle('light', theme === 'light');
    document.documentElement.style.colorScheme = theme;
    window.localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = lang === 'hi' ? 'hi' : 'en';
    window.localStorage.setItem(LANGUAGE_KEY, lang);
  }, [lang]);

  const t = useCallback((key: string) => translations[key]?.[lang] ?? key, [lang]);

  const value = useMemo(() => ({
    theme,
    lang,
    githubConnected,
    aiPanelOpen,
    setTheme,
    setLang,
    setGithubConnected,
    setAiPanelOpen,
    t,
  }), [aiPanelOpen, githubConnected, lang, t, theme]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
}
