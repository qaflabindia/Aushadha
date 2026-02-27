import './App.css';
import '@neo4j-ndl/base/lib/neo4j-ds-styles.css';
import ThemeWrapper from './context/ThemeWrapper';
import { LanguageProvider } from './context/LanguageContext';
import QuickStarter from './components/QuickStarter';
import { GoogleOAuthProvider } from '@react-oauth/google';
import ErrorBoundary from './components/UI/ErrroBoundary';
import { Toaster, SpotlightProvider } from '@neo4j-ndl/react';

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

const Home: React.FC = () => {
  // Always provide GoogleOAuthProvider for both GCS access and app auth
  return (
    <ErrorBoundary>
      <GoogleOAuthProvider clientId={googleClientId}>
        <LanguageProvider>
          <ThemeWrapper>
            <SpotlightProvider>
              <QuickStarter />
            </SpotlightProvider>
            <Toaster />
          </ThemeWrapper>
        </LanguageProvider>
      </GoogleOAuthProvider>
    </ErrorBoundary>
  );
};

export default Home;
