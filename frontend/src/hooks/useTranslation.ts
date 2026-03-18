import { useTranslate } from '../context/TranslationContext';

/**
 * Hook that returns a translation function `t(key)` bound to the current language.
 * BRIDGE: Maps legacy camelCase keys to English phrases, then fetches from backend.
 * Falls back to local i18n.ts if phrase or translation is missing.
 */
export const useTranslation = () => {
  const t_backend = useTranslate();
  return t_backend;
};
