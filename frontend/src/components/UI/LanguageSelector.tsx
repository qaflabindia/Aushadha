import React from 'react';
import { RiGlobalLine } from 'react-icons/ri';
import { useLanguage, SUPPORTED_LANGUAGES } from '../../context/LanguageContext';
import { PremiumDropdown } from './PremiumDropdown';

const LanguageSelector: React.FC = () => {
  const { language, setLanguageByCode } = useLanguage();

  const options = SUPPORTED_LANGUAGES.map((lang) => ({
    label: lang.name,
    value: lang.code,
    description: lang.nameEn,
  }));

  return (
    <PremiumDropdown
      value={language.code}
      options={options}
      onChange={setLanguageByCode}
      icon={<RiGlobalLine />}
      width="200px"
    />
  );
};

export default LanguageSelector;
