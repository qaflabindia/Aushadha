import './App.css';
import '@neo4j-ndl/base/lib/neo4j-ds-styles.css';
import ThemeWrapper from './context/ThemeWrapper';
import { LanguageProvider } from './context/LanguageContext';
import QuickStarter from './components/QuickStarter';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { APP_SOURCES } from './utils/Constants';
import ErrorBoundary from './components/UI/ErrroBoundary';
import { Toaster, SpotlightProvider } from '@neo4j-ndl/react';
const Home: React.FC = () => {
  return (
    <>
      {APP_SOURCES != undefined && APP_SOURCES.includes('gcs') ? (
        <ErrorBoundary>
          <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID as string}>
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
      ) : (
        <ErrorBoundary>
          <LanguageProvider>
            <ThemeWrapper>
              <SpotlightProvider>
                <QuickStarter />
              </SpotlightProvider>
              <Toaster />
            </ThemeWrapper>
          </LanguageProvider>
        </ErrorBoundary>
      )}
    </>
  );
};

export default Home;

