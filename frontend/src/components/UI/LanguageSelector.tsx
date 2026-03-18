import { RiGlobalLine } from 'react-icons/ri';
import { useLanguage } from '../../context/LanguageContext';
import { SUPPORTED_LANGUAGES } from '../../context/LangTypes';
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
      width='200px'
    />
  );
};

export default LanguageSelector;
