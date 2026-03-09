/**
 * TranslationContext — DB-backed i18n with LLM auto-generation.
 *
 * Replaces the static useTranslation() from LanguageContext.
 * - On language switch: batch-fetches ALL known UI strings from /translate/ui/batch
 * - In-memory cache → synchronous t('English Text') after first load
 * - Falls back to English if backend is unreachable
 * - Integrates with existing LanguageContext (no change to LanguageSelector)
 */
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  FC,
} from 'react';
import { useLanguage } from './LanguageContext';

// All known UI strings used in the app. Matches KNOWN_UI_STRINGS in translation_router.py
export const KNOWN_UI_STRINGS: string[] = [
  'File Management', 'Clinical Intelligence', 'DB Connection',
  'No Graph Schema configured', 'Name', 'Status', 'Upload Status',
  'Size (KB)', 'Source', 'Type', 'Model', 'Nodes', 'Completed',
  'Uploaded', 'Local File', 'Generate Graph', 'Delete Files',
  'Preview Graph', 'Graph Settings', 'LLM Model for Processing & Chat',
  'Intelligence Search', 'Medical Intelligence', 'Select Language',
  'Data Insights', 'Knowledge Graph', 'Secret Vault', 'Generated Graph',
  'We are visualizing 50 chunks at a time', 'Document & Chunk',
  'Entities', 'Result Overview', 'Total Nodes', 'Relationships',
  'Search On Node Properties', 'Inquire Vault Intelligence',
  'Authorized Terminal', 'Concierge Intelligence', 'Details', 'Show', 'Page',
  'Large files may be partially processed up to 10K characters due to resource limit.',
  'Welcome to Concierge Intelligence. You can ask questions related to documents which have been completely processed.',
  'AyushPragya Medical Neural Network', 'Select one or more files to delete',
  'Preview generated graph.', 'Visualize the graph in Bloom',
  'File/Files to be deleted', 'Documentation', 'GitHub Issues',
  'Light / Dark mode', 'Entity Graph Extraction Settings', 'Start a chat',
  'Upload files', 'Delete', 'Maximise', 'Copy to Clipboard', 'Copied',
  'Stop Speaking', 'Text to Speech', 'Define schema from text',
  'Fetch schema from database', 'Clear Chat History', 'Continue',
  'Clear configured Graph Schema', 'Apply Graph Schema', 'Chat',
  'Download Conversation', 'Visualize Graph Schema',
  'Analyze instructions for schema', 'Predefined Schema',
  'Data Importer JSON', 'Explore Graph', 'Preview Graph',
  'Documents, Images, Unstructured text', 'Youtube', 'GCS', 'Amazon S3',
  'No Labels Found in the Database',
  'Drop your neo4j credentials file here',
  'Analyze text to extract graph schema', 'Connect', 'Disconnect',
  'Submit', 'Connect to DB', 'Cancel', 'Apply',
  'Provide Additional Instructions for Entity Extractions',
  'Analyze Instructions',
  'Provide specific instructions for entity extraction, such as focusing on the key topics.',
  'JSON Documents',
  'Files are still processing, please select individual checkbox for deletion',
  'Cancel the processing job',
  'Clinical Intelligence Platform', 'Sign in with credentials',
  'Continue in read-only mode', 'Email', 'Password', 'Signing in...', 'Sign In',
  'Patient Insights', 'Global Research', 'Administration', 'AI Assistant',
  'Are you sure you want to delete the selected files?',
  'This action cannot be undone.', 'Confirm', 'Close',
  'Large file detected', 'File exceeds recommended size',
  'Retry', 'Processing failed. Would you like to retry?',
  'No labels found', 'Connection settings', 'Vector index mismatch',
  'Processing & Chat', 'processing & chat',
];

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

async function batchFetch(
  texts: string[],
  lang: string
): Promise<Record<string, string>> {
  try {
    const res = await fetch(`${BACKEND}/translate/ui/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texts, lang }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.translations as Record<string, string>;
  } catch (e) {
    console.warn('[TranslationContext] batch fetch failed, using English fallback', e);
    return {};
  }
}

// ─── Provider ────────────────────────────────────────────────────────────────
export const TranslationProvider: FC<{ children: React.ReactNode }> = ({ children }) => {
  const { language } = useLanguage();
  // cache: { [lang]: { [english]: translated } }
  const cacheRef = useRef<Record<string, Record<string, string>>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [, setTick] = useState(0); // force re-render after cache fill

  useEffect(() => {
    const lang = language.code;
    if (lang === 'en') {
      setTick((n) => n + 1);
      return;
    }

    // Already cached for this language
    if (cacheRef.current[lang] && Object.keys(cacheRef.current[lang]).length > 0) {
      setTick((n) => n + 1);
      return;
    }

    setIsLoading(true);
    batchFetch(KNOWN_UI_STRINGS, lang).then((translations) => {
      cacheRef.current[lang] = translations;
      setIsLoading(false);
      setTick((n) => n + 1); // trigger re-render so components pick up translations
    });
  }, [language.code]);

  const t = useCallback(
    (english: string): string => {
      const lang = language.code;
      if (lang === 'en') return english;
      const translated = cacheRef.current[lang]?.[english];
      return translated || english; // English fallback
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [language.code, isLoading]
  );

  return (
    <TranslationContext.Provider value={{ t, isLoading }}>
      {children}
    </TranslationContext.Provider>
  );
};

/** Hook: returns t() function for the current language. */
export const useTranslate = (): ((english: string) => string) => {
  return useContext(TranslationContext).t;
};

/** Hook: returns full context including loading state */
export const useTranslation2 = (): TranslationContextType => {
  return useContext(TranslationContext);
};

export default TranslationProvider;
