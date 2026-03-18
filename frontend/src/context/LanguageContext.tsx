import React, { createContext, useContext, useState, FC, useCallback } from 'react';
import { SUPPORTED_LANGUAGES, AppLanguage } from './LangTypes';

interface LanguageContextType {
  language: AppLanguage;
  setLanguageByCode: (code: string) => void;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

interface LanguageProviderProps {
  children: React.ReactNode;
}

export const LanguageProvider: FC<LanguageProviderProps> = ({ children }) => {
  const stored = localStorage.getItem('appLanguage');
  const initial = SUPPORTED_LANGUAGES.find((l) => l.code === stored) || SUPPORTED_LANGUAGES[0];
  const [language, setLanguage] = useState<AppLanguage>(initial);

  const setLanguageByCode = useCallback(
    (code: string) => {
      const found = SUPPORTED_LANGUAGES.find((l) => l.code === code);
      if (found && found.code !== language.code) {
        localStorage.setItem('appLanguage', found.code);
        setLanguage(found);
      }
    },
    [language.code]
  );

  return <LanguageContext.Provider value={{ language, setLanguageByCode }}>{children}</LanguageContext.Provider>;
};

export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
