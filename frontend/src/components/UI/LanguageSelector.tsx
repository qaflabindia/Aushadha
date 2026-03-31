import { useState } from 'react';
import { RiGlobalLine } from 'react-icons/ri';
import { useLanguage } from '../../context/LanguageContext';
import { SUPPORTED_LANGUAGES } from '../../context/LangTypes';
import { PremiumDropdown } from './PremiumDropdown';
import { useTranslate } from '../../context/TranslationContext';

const LanguageSelector: React.FC = () => {
  const { language, setLanguageByCode } = useLanguage();
  const t = useTranslate();
  const [isSwitching, setIsSwitching] = useState(false);
  const apiBase = import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000';

  const options = SUPPORTED_LANGUAGES.map((lang) => ({
    label: lang.name,
    value: lang.code,
    description: lang.nameEn,
  }));

  const waitForTranslationCoverage = async (langCode: string) => {
    const startedAt = Date.now();
    const maxWaitMs = 120000;

    while (Date.now() - startedAt < maxWaitMs) {
      const response = await fetch(`${apiBase}/translate/ui/stats`);
      if (!response.ok) {
        throw new Error(`Unable to fetch translation coverage: HTTP ${response.status}`);
      }

      const stats = await response.json();
      const totalKeys = stats?.total_keys ?? 0;
      const langStats = stats?.by_language?.[langCode];
      const translated = langStats?.translated ?? 0;

      if (totalKeys === 0 || translated >= totalKeys) {
        return;
      }

      await new Promise((resolve) => window.setTimeout(resolve, 1500));
    }

    throw new Error(`Timed out while waiting for ${langCode} translations to finish`);
  };

  const handleLanguageChange = async (nextCode: string) => {
    if (nextCode === language.code || isSwitching) {
      return;
    }

    const shouldProceed = window.confirm(
      t(
        'Changing the interface language will refresh the site after translations are prepared. Do you want to continue?'
      )
    );

    if (!shouldProceed) {
      return;
    }

    setIsSwitching(true);

    try {
      if (nextCode !== 'en') {
        const token = localStorage.getItem('aushadha_auth_token');
        const response = await fetch(`${apiBase}/translate/ui/seed?lang=${encodeURIComponent(nextCode)}`, {
          method: 'POST',
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });

        const payload = await response.json().catch(() => ({}));
        if (!response.ok || payload?.status === 'Failed') {
          throw new Error(payload?.error || payload?.message || `HTTP ${response.status}`);
        }

        await waitForTranslationCoverage(nextCode);
      }

      localStorage.removeItem(`aushadha_ui_trans_v2_${nextCode}`);
      setLanguageByCode(nextCode);
      window.alert(t('The interface language has been updated. The site will now refresh.'));
      window.location.reload();
    } catch (error) {
      console.error('Language switch seeding failed', error);
      window.alert(t('Unable to prepare interface translations right now. Please try again.'));
      setLanguageByCode(language.code);
      localStorage.setItem('appLanguage', language.code);
    } finally {
      setIsSwitching(false);
    }
  };

  return (
    <PremiumDropdown
      value={language.code}
      options={options}
      onChange={handleLanguageChange}
      icon={<RiGlobalLine />}
      width='200px'
      disabled={isSwitching}
    />
  );
};

export default LanguageSelector;
