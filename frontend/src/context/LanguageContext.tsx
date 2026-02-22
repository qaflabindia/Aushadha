import React, { createContext, useContext, useState, FC, useCallback } from 'react';
import { getTranslation, TranslationKey } from '../utils/i18n';

export interface AppLanguage {
  code: string;       // ISO 639-1 (e.g., 'en', 'hi', 'ta')
  speechCode: string;  // BCP 47 for Web Speech API (e.g., 'en-US', 'hi-IN')
  name: string;        // Display name in that language
  nameEn: string;      // Display name in English
}

export const SUPPORTED_LANGUAGES: AppLanguage[] = [
  { code: 'en', speechCode: 'en-US', name: 'English',  nameEn: 'English' },
  { code: 'hi', speechCode: 'hi-IN', name: 'हिन्दी',    nameEn: 'Hindi' },
  { code: 'ta', speechCode: 'ta-IN', name: 'தமிழ்',     nameEn: 'Tamil' },
  { code: 'te', speechCode: 'te-IN', name: 'తెలుగు',    nameEn: 'Telugu' },
  { code: 'bn', speechCode: 'bn-IN', name: 'বাংলা',     nameEn: 'Bengali' },
  { code: 'mr', speechCode: 'mr-IN', name: 'मराठी',     nameEn: 'Marathi' },
  { code: 'kn', speechCode: 'kn-IN', name: 'ಕನ್ನಡ',     nameEn: 'Kannada' },
  { code: 'ml', speechCode: 'ml-IN', name: 'മലയാളം',    nameEn: 'Malayalam' },
  { code: 'gu', speechCode: 'gu-IN', name: 'ગુજરાતી',   nameEn: 'Gujarati' },
  { code: 'pa', speechCode: 'pa-IN', name: 'ਪੰਜਾਬੀ',    nameEn: 'Punjabi' },
  { code: 'or', speechCode: 'or-IN', name: 'ଓଡ଼ିଆ',     nameEn: 'Odia' },
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
  const initial = SUPPORTED_LANGUAGES.find(l => l.code === stored) || SUPPORTED_LANGUAGES[0];
  const [language, setLanguage] = useState<AppLanguage>(initial);

  const setLanguageByCode = useCallback((code: string) => {
    const found = SUPPORTED_LANGUAGES.find(l => l.code === code);
    if (found) {
      setLanguage(found);
      localStorage.setItem('appLanguage', code);
    }
  }, []);

  return (
    <LanguageContext.Provider value={{ language, setLanguageByCode }}>
      {children}
    </LanguageContext.Provider>
  );
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
 * Usage: const t = useTranslation(); <span>{t('fileManagement')}</span>
 */
export const useTranslation = () => {
  const { language } = useLanguage();
  return useCallback(
    (key: TranslationKey) => getTranslation(language.code, key),
    [language.code]
  );
};
