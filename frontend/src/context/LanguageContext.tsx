import React, { createContext, useContext, useState, FC, useCallback } from 'react';
import { useTranslate } from './TranslationContext';
import localTranslations, { TranslationKey } from '../utils/i18n';

export interface AppLanguage {
  code: string; // ISO 639-1 (e.g., 'en', 'hi', 'ta')
  speechCode: string; // BCP 47 for Web Speech API (e.g., 'en-US', 'hi-IN')
  name: string; // Display name in that language
  nameEn: string; // Display name in English
}

export const SUPPORTED_LANGUAGES: AppLanguage[] = [
  { code: 'en', speechCode: 'en-US', name: 'English', nameEn: 'English' },
  { code: 'hi', speechCode: 'hi-IN', name: 'हिन्दी', nameEn: 'Hindi' },
  { code: 'ta', speechCode: 'ta-IN', name: 'தமிழ்', nameEn: 'Tamil' },
  { code: 'te', speechCode: 'te-IN', name: 'తెలుగు', nameEn: 'Telugu' },
  { code: 'bn', speechCode: 'bn-IN', name: 'বাংলা', nameEn: 'Bengali' },
  { code: 'mr', speechCode: 'mr-IN', name: 'मराठी', nameEn: 'Marathi' },
  { code: 'kn', speechCode: 'kn-IN', name: 'ಕನ್ನಡ', nameEn: 'Kannada' },
  { code: 'ml', speechCode: 'ml-IN', name: 'മലയാളം', nameEn: 'Malayalam' },
  { code: 'gu', speechCode: 'gu-IN', name: 'ગુજરાતી', nameEn: 'Gujarati' },
  { code: 'pa', speechCode: 'pa-IN', name: 'ਪੰਜਾਬੀ', nameEn: 'Punjabi' },
  { code: 'or', speechCode: 'or-IN', name: 'ଓଡ଼ିଆ', nameEn: 'Odia' },
];

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
  const [language] = useState<AppLanguage>(initial);

  const setLanguageByCode = useCallback(
    (code: string) => {
      const found = SUPPORTED_LANGUAGES.find((l) => l.code === code);
      if (found && found.code !== language.code) {
        const confirmed = window.confirm(
          `Changing the language to ${found.name} requires refreshing the application. Any unsaved work may be lost. Proceed?`
        );
        if (confirmed) {
          localStorage.setItem('appLanguage', code);
          window.location.reload();
        }
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

/**
 * Hook that returns a translation function `t(key)` bound to the current language.
 * BRIDGE: Maps legacy camelCase keys to English phrases, then fetches from backend.
 * Falls back to local i18n.ts if phrase or translation is missing.
 */
export const useTranslation = () => {
  const { language } = useLanguage();
  const t_backend = useTranslate();

  return useCallback(
    (key: TranslationKey) => {
      // 1. Map key to English phrase using local i18n.ts
      const englishPhrase = localTranslations.en[key];

      if (!englishPhrase) {
        // eslint-disable-next-line no-console
        console.warn(`[LanguageBridge] No English phrase found for key: ${key}`);
        return key;
      }

      // 2. Fetch translation from backend system
      const translated = t_backend(englishPhrase);

      // 3. Safety Fallback: if backend returns the phrase itself (not translated)
      // AND we have a local translation for this specific language, we COULD use it.
      // But for "minimum code", we trust the backend's passthrough/fallback logic.
      if (translated === englishPhrase && language.code !== 'en') {
        const localFallback = (localTranslations as any)[language.code]?.[key];
        if (localFallback) {
          return localFallback;
        }
      }

      return translated;
    },
    [language.code, t_backend]
  );
};
