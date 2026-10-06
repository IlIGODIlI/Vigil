import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import {
  ensureMsalInitialized,
  isEntraConfigured,
  loginRequest,
  msalInstance,
  setAccessToken,
} from './msal';

import { authService } from '../services/authService';

interface AuthUser {
  displayName: string;
  email: string;
}

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: AuthUser | null;
  error: string;

  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string) => Promise<void>;

  signInWithMicrosoft: () => Promise<void>;

  isMicrosoftAvailable: boolean;

  signOut: () => Promise<void>;
  clearError: () => void;
}

const STORAGE_KEY = 'vigil.mock-user';

const AuthContext = createContext<AuthState | null>(null);

function readStoredUser(): AuthUser | null {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);

    return stored
      ? (JSON.parse(stored) as AuthUser)
      : null;
  } catch {
    return null;
  }
}

export function AuthProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [user, setUser] =
    useState<AuthUser | null>(readStoredUser);

  const [isLoading, setIsLoading] =
    useState(isEntraConfigured);

  const [error, setError] = useState('');

  const microsoftInitRan = useRef(false);

  /*
   * Handle Microsoft Entra redirect login
   * and restore an existing Microsoft session.
   */
  useEffect(() => {
    if (!isEntraConfigured || microsoftInitRan.current) {
      setIsLoading(false);
      return;
    }

    microsoftInitRan.current = true;

    let cancelled = false;

    async function completeMicrosoftSignIn() {
      try {
        await ensureMsalInitialized();

        const redirectResult =
          await msalInstance.handleRedirectPromise();

        const account =
          redirectResult?.account ??
          msalInstance.getAllAccounts()[0] ??
          null;

        if (account) {
          msalInstance.setActiveAccount(account);

          const tokenResult =
            redirectResult ??
            (await msalInstance.acquireTokenSilent({
              ...loginRequest,
              account,
            }));

          setAccessToken(tokenResult.accessToken);

          /*
           * Get the logged-in user from SecurePR backend.
           */
          const profile =
            await authService.getCurrentUser();

          if (!cancelled) {
            const nextUser: AuthUser = {
              displayName:
                profile.name ||
                profile.username ||
                account.name ||
                account.username,

              email:
                profile.email ||
                account.username,
            };

            window.localStorage.setItem(
              STORAGE_KEY,
              JSON.stringify(nextUser)
            );

            setUser(nextUser);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : 'Microsoft sign-in could not be completed.'
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    completeMicrosoftSignIn();

    return () => {
      cancelled = true;
    };
  }, []);

  /*
   * Existing email/password authentication.
   * This remains unchanged.
   */
  const completeLocalAuth = useCallback(
    async (nextUser: AuthUser) => {
      setError('');
      setIsLoading(true);

      await new Promise(resolve =>
        window.setTimeout(resolve, 650)
      );

      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(nextUser)
      );

      setUser(nextUser);
      setIsLoading(false);
    },
    []
  );

  const signIn = useCallback(
    async (email: string, password: string) => {
      if (!email.trim() || !password) {
        setError(
          'Enter your email and password to continue.'
        );
        return;
      }

      const nameFromEmail = email
        .split('@')[0]
        .replace(/[._-]+/g, ' ');

      const displayName =
        nameFromEmail.replace(
          /\b\w/g,
          character => character.toUpperCase()
        ) || 'Vigil User';

      await completeLocalAuth({
        displayName,
        email: email.trim().toLowerCase(),
      });
    },
    [completeLocalAuth]
  );

  const signUp = useCallback(
    async (
      name: string,
      email: string,
      password: string
    ) => {
      if (!name.trim() || !email.trim() || !password) {
        setError(
          'Complete all fields to create your account.'
        );
        return;
      }

      await completeLocalAuth({
        displayName: name.trim(),
        email: email.trim().toLowerCase(),
      });
    },
    [completeLocalAuth]
  );

  /*
   * Microsoft Entra login.
   */
  const signInWithMicrosoft = useCallback(
    async () => {
      if (!isEntraConfigured) {
        setError(
          'Microsoft sign-in is not configured for this environment.'
        );
        return;
      }

      setError('');
      setIsLoading(true);

      try {
        await ensureMsalInitialized();

        /*
         * Microsoft login redirects the browser to
         * Microsoft Entra ID.
         */
        await msalInstance.loginRedirect(
          loginRequest
        );
      } catch (err) {
        setIsLoading(false);

        setError(
          err instanceof Error
            ? err.message
            : 'Microsoft sign-in failed. Please try again.'
        );
      }
    },
    []
  );

  const signOut = useCallback(async () => {
    setIsLoading(true);

    window.localStorage.removeItem(STORAGE_KEY);

    setUser(null);
    setError('');

    setAccessToken(null);

    const activeMicrosoftAccount =
      isEntraConfigured
        ? msalInstance.getActiveAccount()
        : null;

    if (activeMicrosoftAccount) {
      try {
        await ensureMsalInitialized();

        await msalInstance.logoutRedirect({
          account: activeMicrosoftAccount,
          postLogoutRedirectUri:
            `${window.location.origin}/`,
        });

        return;
      } catch {
        // Fall through to local logout.
      }
    }

    setIsLoading(false);

    window.location.assign('/');
  }, []);

  const clearError = useCallback(
    () => setError(''),
    []
  );

  const value = useMemo<AuthState>(
    () => ({
      isAuthenticated: Boolean(user),

      isLoading,

      user,

      error,

      signIn,

      signUp,

      signInWithMicrosoft,

      isMicrosoftAvailable:
        isEntraConfigured,

      signOut,

      clearError,
    }),
    [
      clearError,
      error,
      isLoading,
      signIn,
      signInWithMicrosoft,
      signOut,
      signUp,
      user,
    ]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      'useAuth must be used within AuthProvider'
    );
  }

  return context;
}