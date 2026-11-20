import { ReactNode, createContext, useMemo, useState, useEffect } from 'react';
import { NeedleThemeProvider, useMediaQuery } from '@neo4j-ndl/react';
export const ThemeWrapperContext = createContext({
  toggleColorMode: () => {},
  colorMode: localStorage.getItem('mode') as 'light' | 'dark',
});
interface ThemeWrapperProps {
  children: ReactNode;
}

const themeBodyInjection = (mode: 'light' | 'dark') => {
  document.body.classList.toggle('ndl-theme-dark', mode === 'dark');
  document.body.classList.toggle('ndl-theme-light', mode === 'light');
  // Native controls (scrollbars, form fields) follow the active theme too
  document.documentElement.style.colorScheme = mode;
};

const ThemeWrapper = ({ children }: ThemeWrapperProps) => {
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
  // A stored choice wins; with none, the app follows the system theme and keeps following it
  const [storedMode, setStoredMode] = useState<'light' | 'dark' | null>(
    () => localStorage.getItem('mode') as 'light' | 'dark' | null
  );
  const mode: 'light' | 'dark' = storedMode ?? (prefersDarkMode ? 'dark' : 'light');

  useEffect(() => {
    themeBodyInjection(mode);
  }, [mode]);

  const themeWrapperUtils = useMemo(
    () => ({
      colorMode: mode,
      toggleColorMode: () => {
        const newMode = mode === 'light' ? 'dark' : 'light';
        localStorage.setItem('mode', newMode);
        setStoredMode(newMode);
      },
    }),
    [mode]
  );

  return (
    <ThemeWrapperContext.Provider value={themeWrapperUtils}>
      <NeedleThemeProvider theme={mode} wrapperProps={{ isWrappingChildren: false }}>
        {children}
      </NeedleThemeProvider>
    </ThemeWrapperContext.Provider>
  );
};
export default ThemeWrapper;
