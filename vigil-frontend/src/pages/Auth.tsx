import {
  useEffect,
  useState,
  type FormEvent,
} from 'react';

import { useNavigate } from 'react-router-dom';

import {
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  Shield,
  User,
  Zap,
} from 'lucide-react';

import { useAuth } from '../auth/AuthContext';

import neuralNetworkBackground from '../imports/ChatGPT_Image_Sep_26__2026__11_27_24_PM.png';

interface AuthProps {
  mode: 'signin' | 'signup';
}

export default function Auth({
  mode,
}: AuthProps) {
  const navigate = useNavigate();

  const {
    signIn,
    signUp,
    signInWithMicrosoft,
    isMicrosoftAvailable,
    isLoading,
    error,
    clearError,
  } = useAuth();

  const isSignup = mode === 'signup';

  const [name, setName] = useState('');
  const [email, setEmail] =
    useState('');
  const [password, setPassword] =
    useState('');

  const [confirmPassword, setConfirmPassword] =
    useState('');

  const [showPassword, setShowPassword] =
    useState(false);

  const [validationError, setValidationError] =
    useState('');

  useEffect(() => {
    clearError();
    setValidationError('');
  }, [clearError, mode]);

  const handleSubmit = async (
    event: FormEvent
  ) => {
    event.preventDefault();

    setValidationError('');

    if (!email.includes('@')) {
      setValidationError(
        'Enter a valid work email address.'
      );
      return;
    }

    if (password.length < 8) {
      setValidationError(
        'Password must contain at least 8 characters.'
      );
      return;
    }

    if (
      isSignup &&
      password !== confirmPassword
    ) {
      setValidationError(
        'Passwords do not match.'
      );
      return;
    }

    if (isSignup) {
      await signUp(
        name,
        email,
        password
      );
    } else {
      await signIn(
        email,
        password
      );
    }

    navigate('/dashboard');
  };

  return (
    <div className="auth-page">

      <aside className="auth-brand-panel">

        <img
          className="auth-brand-background"
          src={neuralNetworkBackground}
          alt=""
          aria-hidden="true"
        />

        <button
          className="vigil-wordmark"
          onClick={() => navigate('/')}
          aria-label="Vigil home"
        >
          <span>
            <Zap
              size={13}
              strokeWidth={2.5}
            />
          </span>

          vigil
        </button>

        <div className="auth-brand-content">

          <div className="auth-security-tag">
            <span className="dot dot-safe dot-pulse" />

            Secure workspace access
          </div>

          <h2>
            Security that
            <br />

            <span>
              works with you.
            </span>
          </h2>

          <p>
            Review security before it
            reaches production. Understand
            every risk and keep the final
            decision with your team.
          </p>

        </div>

        <div className="auth-trust-list">

          {[
            'Read-only GitHub access — no write permissions',
            'SOC 2 Type II compliant infrastructure',
            'Full audit trail of every review and decision',
          ].map(text => (
            <div key={text}>

              <Shield size={12} />

              <span>
                {text}
              </span>

            </div>
          ))}

        </div>

      </aside>

      <main className="auth-form-area">

        <div className="auth-form-shell">

          <button
            className="btn btn-ghost btn-sm auth-back"
            onClick={() => navigate('/')}
          >
            <ArrowLeft size={12} />

            Back to Vigil
          </button>

          <div className="auth-mobile-brand">

            <button
              className="vigil-wordmark"
              onClick={() => navigate('/')}
            >
              <span>
                <Zap size={13} />
              </span>

              vigil
            </button>

          </div>

          <div className="auth-heading">

            <div className="auth-heading-icon">

              {isSignup ? (
                <User size={17} />
              ) : (
                <LockKeyhole size={17} />
              )}

            </div>

            <h1>
              {isSignup
                ? 'Create your account'
                : 'Welcome back'}
            </h1>

            <p>
              {isSignup
                ? 'Set up your Vigil workspace in a few seconds.'
                : 'Sign in to continue to your security workspace.'}
            </p>

          </div>

          <form
            className="auth-form"
            onSubmit={handleSubmit}
          >

            {isSignup && (
              <label className="auth-field">

                <span>Name</span>

                <div>

                  <User size={14} />

                  <input
                    value={name}
                    onChange={event =>
                      setName(
                        event.target.value
                      )
                    }
                    placeholder="Your full name"
                    autoComplete="name"
                    required
                  />

                </div>

              </label>
            )}

            <label className="auth-field">

              <span>Email</span>

              <div>

                <Mail size={14} />

                <input
                  type="email"
                  value={email}
                  onChange={event =>
                    setEmail(
                      event.target.value
                    )
                  }
                  placeholder="you@company.com"
                  autoComplete="email"
                  required
                />

              </div>

            </label>

            <label className="auth-field">

              <span>Password</span>

              <div>

                <LockKeyhole size={14} />

                <input
                  type={
                    showPassword
                      ? 'text'
                      : 'password'
                  }
                  value={password}
                  onChange={event =>
                    setPassword(
                      event.target.value
                    )
                  }
                  placeholder="At least 8 characters"
                  autoComplete={
                    isSignup
                      ? 'new-password'
                      : 'current-password'
                  }
                  required
                />

                <button
                  type="button"
                  onClick={() =>
                    setShowPassword(
                      value => !value
                    )
                  }
                  aria-label={
                    showPassword
                      ? 'Hide password'
                      : 'Show password'
                  }
                >
                  {showPassword ? (
                    <EyeOff size={14} />
                  ) : (
                    <Eye size={14} />
                  )}
                </button>

              </div>

            </label>

            {isSignup && (
              <label className="auth-field">

                <span>
                  Confirm password
                </span>

                <div>

                  <LockKeyhole size={14} />

                  <input
                    type={
                      showPassword
                        ? 'text'
                        : 'password'
                    }
                    value={confirmPassword}
                    onChange={event =>
                      setConfirmPassword(
                        event.target.value
                      )
                    }
                    placeholder="Repeat your password"
                    autoComplete="new-password"
                    required
                  />

                </div>

              </label>
            )}

            {(validationError ||
              error) && (
              <div
                className="auth-error"
                role="alert"
              >
                {validationError ||
                  error}
              </div>
            )}

            <button
              className="btn btn-primary btn-lg auth-submit"
              type="submit"
              disabled={isLoading}
            >

              {isLoading && (
                <span className="auth-loader" />
              )}

              {isLoading
                ? isSignup
                  ? 'Creating account…'
                  : 'Signing in…'
                : isSignup
                  ? 'Create Account'
                  : 'Sign In'}

              {!isLoading && (
                <ArrowRight size={14} />
              )}

            </button>

          </form>

          <div className="auth-divider">
            <span>or</span>
          </div>

          {/* Microsoft Entra ID login */}

          <button
            className="btn btn-secondary btn-lg auth-microsoft"
            type="button"
            onClick={signInWithMicrosoft}
            disabled={
              isLoading ||
              !isMicrosoftAvailable
            }
            title={
              isMicrosoftAvailable
                ? undefined
                : 'Microsoft authentication is not configured for this environment.'
            }
          >

            <span className="microsoft-mark">

              <i />
              <i />
              <i />
              <i />

            </span>

            Continue with Microsoft

            {!isMicrosoftAvailable && (
              <small>
                Not configured
              </small>
            )}

          </button>

          <p className="auth-switch">

            {isSignup
              ? 'Already have an account?'
              : 'New to Vigil?'}

            <button
              onClick={() =>
                navigate(
                  isSignup
                    ? '/login'
                    : '/signup'
                )
              }
            >
              {isSignup
                ? 'Sign In'
                : 'Create Account'}
            </button>

          </p>

          <p className="auth-terms">
            By continuing, you agree to
            Vigil’s Terms of Service and
            Privacy Policy.
          </p>

          {!isSignup && (
            <div className="auth-local-note">

              <CheckCircle size={11} />

              Local preview authentication
              is active. No credentials are
              stored.

            </div>
          )}

        </div>

      </main>

    </div>
  );
}