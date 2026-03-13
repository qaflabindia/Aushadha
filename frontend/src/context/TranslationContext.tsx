/**
 * TranslationContext — DB-backed i18n with LLM auto-generation.
 *
 * Replaces the static useTranslation() from LanguageContext.
 * - On language switch: batch-fetches ALL known UI strings from /translate/ui/batch
 * - In-memory cache → synchronous t('English Text') after first load
 * - Falls back to English if backend is unreachable
 * - Integrates with existing LanguageContext (no change to LanguageSelector)
 */
import React, { createContext, useContext, useState, useEffect, useCallback, useRef, FC } from 'react';
import { useLanguage } from './LanguageContext';

// ─── Context types ────────────────────────────────────────────────────────────

// ─── Context types ────────────────────────────────────────────────────────────
interface TranslationContextType {
  /** Translate an English string to the current language. Synchronous after load. */
  t: (english: string) => string;
  /** Whether the batch fetch for the current language is loading */
  isLoading: boolean;
}

const TranslationContext = createContext<TranslationContextType>({
  t: (s) => s,
  isLoading: false,
});

// ─── Helpers ──────────────────────────────────────────────────────────────────
const BACKEND = import.meta.env.VITE_BACKEND_API_URL ?? '';

async function batchFetch(texts: string[], lang: string): Promise<Record<string, string>> {
  try {
    const res = await fetch(`${BACKEND}/translate/ui/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texts, lang }),
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const data = await res.json();
    return data.translations as Record<string, string>;
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('[TranslationContext] batch fetch failed, using English fallback', e);
    return {};
  }
}

// ─── Provider ────────────────────────────────────────────────────────────────
export const TranslationProvider: FC<{ children: React.ReactNode }> = ({ children }) => {
  const { language } = useLanguage();
  // cache: { [lang]: { [english]: translated } }
  const cacheRef = useRef<Record<string, Record<string, string>>>({});
  const [knownStrings, setKnownStrings] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [, setTick] = useState(0); // force re-render after cache fill

  // 1. Fetch the master list of UI strings once on mount
  useEffect(() => {
    fetch(`${BACKEND}/translate/ui/strings`)
      .then((res) => res.json())
      .then((data) => {
        setKnownStrings(data.strings || []);
      })
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.error('[TranslationContext] Failed to fetch known strings', err);
      });
  }, []);

  // 2. Fetch translations when language changes or knownStrings is loaded
  useEffect(() => {
    const lang = language.code;
    if (lang === 'en' || knownStrings.length === 0) {
      setTick((n) => n + 1);
      return;
    }

    // Already cached for this language
    if (cacheRef.current[lang] && Object.keys(cacheRef.current[lang]).length > 0) {
      setTick((n) => n + 1);
      return;
    }

    setIsLoading(true);
    const startTime = performance.now();
    batchFetch(knownStrings, lang).then((translations) => {
      const duration = performance.now() - startTime;
      // eslint-disable-next-line no-console
      console.log(
        `[TranslationContext] Loaded ${Object.keys(translations).length} strings for '${lang}' in ${duration.toFixed(2)}ms`
      );
      cacheRef.current[lang] = translations;
      setIsLoading(false);
      setTick((n) => n + 1); // trigger re-render so components pick up translations
    });
  }, [language.code, knownStrings]);

  const t = useCallback(
    (english: string): string => {
      const lang = language.code;
      if (lang === 'en') {
        return english;
      }
      const translated = cacheRef.current[lang]?.[english];
      return translated || english; // English fallback
    },
    [language.code]
  );

  return <TranslationContext.Provider value={{ t, isLoading }}>{children}</TranslationContext.Provider>;
};

/** Hook: returns t() function for the current language. */
export function useTranslate(): (english: string) => string {
  const context = useContext(TranslationContext);
  const { t } = context;
  return t;
}

/** Hook: returns full context including loading state */
export function useTranslation2(): TranslationContextType {
  const context = useContext(TranslationContext);
  return context;
}

export default TranslationProvider;
