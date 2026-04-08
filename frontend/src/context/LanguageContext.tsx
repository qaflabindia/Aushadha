import React, { createContext, useContext, useState, FC, useCallback, useEffect } from 'react';
import { SUPPORTED_LANGUAGES, AppLanguage } from './LangTypes';

interface LanguageContextType {
  language: AppLanguage;
  setLanguageByCode: (code: string) => void;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);
const GLOBAL_LANGUAGE_KEY = 'appLanguage';
const USER_LANGUAGE_KEY_PREFIX = 'appLanguage:';
const AUTH_USER_KEY = 'aushadha_auth_user';
const AUTH_CHANGED_EVENT = 'aushadha-auth-changed';

interface LanguageProviderProps {
  children: React.ReactNode;
}

const getStoredAuthEmail = (): string | null => {
  try {
    const storedUser = localStorage.getItem(AUTH_USER_KEY);
    if (!storedUser) {
      return null;
    }

    const parsedUser = JSON.parse(storedUser) as { email?: string };
    return parsedUser?.email?.trim().toLowerCase() || null;
  } catch {
    return null;
  }
};

const getStoredLanguageCode = (): string | null => {
  const email = getStoredAuthEmail();
  const userSpecificCode = email ? localStorage.getItem(`${USER_LANGUAGE_KEY_PREFIX}${email}`) : null;
  return userSpecificCode || localStorage.getItem(GLOBAL_LANGUAGE_KEY);
};

const resolveLanguage = (): AppLanguage => {
  const storedCode = getStoredLanguageCode();
  return SUPPORTED_LANGUAGES.find((lang) => lang.code === storedCode) || SUPPORTED_LANGUAGES[0];
};

const persistLanguageSelection = (code: string) => {
  localStorage.setItem(GLOBAL_LANGUAGE_KEY, code);

  const email = getStoredAuthEmail();
  if (email) {
    localStorage.setItem(`${USER_LANGUAGE_KEY_PREFIX}${email}`, code);
  }
};

export const LanguageProvider: FC<LanguageProviderProps> = ({ children }) => {
  const initial = resolveLanguage();
  const [language, setLanguage] = useState<AppLanguage>(initial);

  useEffect(() => {
    const syncLanguageFromStorage = () => {
      const nextLanguage = resolveLanguage();
      setLanguage((currentLanguage) => (currentLanguage.code === nextLanguage.code ? currentLanguage : nextLanguage));
    };

    const handleStorage = (event: StorageEvent) => {
      if (
        !event.key ||
        event.key === GLOBAL_LANGUAGE_KEY ||
        event.key === AUTH_USER_KEY ||
        event.key.startsWith(USER_LANGUAGE_KEY_PREFIX)
      ) {
        syncLanguageFromStorage();
      }
    };

    window.addEventListener('storage', handleStorage);
    window.addEventListener(AUTH_CHANGED_EVENT, syncLanguageFromStorage);

    return () => {
      window.removeEventListener('storage', handleStorage);
      window.removeEventListener(AUTH_CHANGED_EVENT, syncLanguageFromStorage);
    };
  }, []);

  const setLanguageByCode = useCallback(
    (code: string) => {
      const found = SUPPORTED_LANGUAGES.find((l) => l.code === code);
      if (found && found.code !== language.code) {
        persistLanguageSelection(found.code);
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
