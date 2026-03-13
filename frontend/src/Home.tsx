import './App.css';
import '@neo4j-ndl/base/lib/neo4j-ds-styles.css';
import ThemeWrapper from './context/ThemeWrapper';
import QuickStarter from './components/QuickStarter';
import ErrorBoundary from './components/UI/ErrroBoundary';
import { Toaster, SpotlightProvider } from '@neo4j-ndl/react';

const Home: React.FC = () => {
  return (
    <ErrorBoundary>
      <ThemeWrapper>
        <SpotlightProvider>
          <QuickStarter />
        </SpotlightProvider>
        <Toaster />
      </ThemeWrapper>
    </ErrorBoundary>
  );
};

export default Home;
