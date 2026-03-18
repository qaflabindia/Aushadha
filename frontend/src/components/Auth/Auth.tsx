// =============================================================================
// Aushadha — Authentication Component
// =============================================================================
// Replaces Auth0 with Google Sign-In + Local Login (RSA-256 JWT).
// The SKIP_AUTH flag still works — when true, auth is bypassed entirely.
// =============================================================================

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { GoogleLogin, CredentialResponse } from '@react-oauth/google';
import { useGoogleAuth } from '../../context/GoogleAuthContext';
import { useTranslate } from '../../context/TranslationContext';
import LanguageSelector from '../UI/LanguageSelector';

// ---------------------------------------------------------------------------
// Authentication Guard — wraps protected routes
// ---------------------------------------------------------------------------
export const AuthenticationGuard: React.FC<{ component: React.ComponentType<object> }> = ({ component }) => {
  const { isAuthenticated, isLoading } = useGoogleAuth();
  const Component = component;
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      // Don't redirect if we are already on login
      if (window.location.pathname !== '/login') {
        localStorage.setItem('isReadOnlyMode', 'true');
        navigate('/login', { replace: true });
      }
    }
  }, [isLoading, isAuthenticated, navigate]);

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <p>Loading...</p>
      </div>
    );
  }

  return <Component />;
};

// ---------------------------------------------------------------------------
// Login Page — Google + Local auth options
// ---------------------------------------------------------------------------
export const LoginPage: React.FC = () => {
  const { loginWithGoogleDetailed, loginWithLocal, isAuthenticated } = useGoogleAuth();
  const navigate = useNavigate();
  const t = useTranslate();

  const [showLocalLogin, setShowLocalLogin] = useState(false);
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      localStorage.removeItem('isReadOnlyMode');
      navigate('/', { replace: true });
    }
  }, [isAuthenticated]);

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (credentialResponse.credential) {
      setLoading(true);
      setError('');
      const result = await loginWithGoogleDetailed(credentialResponse.credential);
      setLoading(false);
      if (!result.success) {
        setError(result.message || 'Google authentication failed. Please try again.');
      }
    }
  };

  const handleLocalLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!usernameOrEmail.trim() || !password.trim()) {
      setError('Username/Email and password are required');
      return;
    }
    setLoading(true);
    setError('');
    const result = await loginWithLocal(usernameOrEmail, password);
    setLoading(false);
    if (!result.success) {
      setError(result.message);
    }
  };

  return (
    <div style={styles.container}>
      <div style={{ position: 'absolute', top: '16px', right: '24px' }}>
        <LanguageSelector />
      </div>
      <div style={styles.card}>
        {/* Logo / Branding */}
        <div style={styles.header}>
          <h1 style={styles.title}>AyushPragya</h1>
          <p style={styles.subtitle}>{t('Clinical Intelligence Platform')}</p>
        </div>

        {error && <div style={styles.errorBanner}>{error}</div>}

        {/* Google Sign-In */}
        <div style={styles.googleSection}>
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => setError('Google Sign-In failed')}
            theme='outline'
            size='large'
            width='320'
            text='signin_with'
          />
        </div>

        {/* Divider */}
        <div style={styles.divider}>
          <span style={styles.dividerText}>or</span>
        </div>

        {/* Local Login Toggle */}
        {!showLocalLogin ? (
          <button style={styles.localToggle} onClick={() => setShowLocalLogin(true)}>
            {t('Sign in with credentials')}
          </button>
        ) : (
          <form onSubmit={handleLocalLogin} style={styles.form}>
            <input
              type='text'
              placeholder={t('Username / Email')}
              value={usernameOrEmail}
              onChange={(e) => setUsernameOrEmail(e.target.value)}
              style={styles.input}
              autoFocus
            />
            <input
              type='password'
              placeholder={t('Password')}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
            />
            <button type='submit' style={styles.submitBtn} disabled={loading}>
              {loading ? t('Signing in...') : t('Sign In')}
            </button>
          </form>
        )}

        {/* Read-Only Mode */}
        <button
          style={styles.readonlyLink}
          onClick={() => {
            localStorage.setItem('isReadOnlyMode', 'true');
            navigate('/readonly', { replace: true });
          }}
        >
          {t('Continue in read-only mode')} →
        </button>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Admin Guard — restricts to Admin role
// ---------------------------------------------------------------------------
export const AdminGuard: React.FC<{ component: React.ComponentType<any> }> = ({ component: Component }) => {
  const { isAuthenticated, isLoading, user } = useGoogleAuth();

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <p>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to='/login' />;
  }

  if (user?.role?.toUpperCase() !== 'ADMIN') {
    return <Navigate to='/' />;
  }

  return <Component />;
};

const Navigate: React.FC<{ to: string }> = ({ to }) => {
  const navigate = useNavigate();
  useEffect(() => {
    navigate(to, { replace: true });
  }, [to, navigate]);
  return null;
};

// ---------------------------------------------------------------------------
// Inline Styles (no external CSS dependencies)
// ---------------------------------------------------------------------------
const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  },
  card: {
    background: 'rgba(30, 41, 59, 0.9)',
    backdropFilter: 'blur(20px)',
    borderRadius: '16px',
    padding: '48px 40px',
    width: '400px',
    maxWidth: '90vw',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
    border: '1px solid rgba(148, 163, 184, 0.1)',
  },
  header: {
    textAlign: 'center' as const,
    marginBottom: '32px',
  },
  title: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#f1f5f9',
    margin: '0 0 8px 0',
    letterSpacing: '-0.02em',
  },
  subtitle: {
    fontSize: '14px',
    color: '#94a3b8',
    margin: 0,
  },
  errorBanner: {
    background: 'rgba(239, 68, 68, 0.15)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '8px',
    padding: '10px 14px',
    marginBottom: '20px',
    color: '#fca5a5',
    fontSize: '13px',
    textAlign: 'center' as const,
  },
  googleSection: {
    display: 'flex',
    justifyContent: 'center',
    marginBottom: '24px',
  },
  divider: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '24px',
  },
  dividerText: {
    color: '#64748b',
    fontSize: '13px',
    flex: 1,
    textAlign: 'center' as const,
    position: 'relative' as const,
  },
  localToggle: {
    width: '100%',
    padding: '12px',
    background: 'transparent',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    borderRadius: '8px',
    color: '#cbd5e1',
    fontSize: '14px',
    cursor: 'pointer',
    marginBottom: '16px',
    transition: 'all 0.2s',
  },
  form: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
    marginBottom: '16px',
  },
  input: {
    padding: '12px 14px',
    background: 'rgba(15, 23, 42, 0.6)',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    borderRadius: '8px',
    color: '#f1f5f9',
    fontSize: '14px',
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  submitBtn: {
    padding: '12px',
    background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
    border: 'none',
    borderRadius: '8px',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'opacity 0.2s',
  },
  readonlyLink: {
    width: '100%',
    padding: '10px',
    background: 'transparent',
    border: 'none',
    color: '#64748b',
    fontSize: '13px',
    cursor: 'pointer',
    textAlign: 'center' as const,
    marginTop: '8px',
  },
};

export default AuthenticationGuard;
