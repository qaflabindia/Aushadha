import { ReusableDropdownProps } from '../types';
import { useMemo } from 'react';
import { capitalize, capitalizeWithUnderscore } from '../utils/Utils';
import { prodllms } from '../utils/Constants';
import { PremiumDropdown } from './UI/PremiumDropdown';
import { RiRobot3Line } from 'react-icons/ri';
import { useTranslate } from '../context/TranslationContext';

const DropdownComponent: React.FC<ReusableDropdownProps> = ({
  options,
  placeholder,
  defaultValue,
  onSelect,
  view,
  value,
}) => {
  const t = useTranslate();
  const isProdEnv = import.meta.env.VITE_ENV === 'PROD';
  // Use 'value' if provided, otherwise fallback to 'defaultValue'
  const currentValue =
    typeof value === 'string'
      ? value
      : value?.value || (typeof defaultValue === 'string' ? defaultValue : defaultValue?.value) || null;

  const handleChange = (newValue: string) => {
    const selectedOpt = options.find((opt) => (typeof opt === 'string' ? opt : opt.value) === newValue);
    if (selectedOpt) {
      onSelect(selectedOpt);
      const existingModel = localStorage.getItem('selectedModel');
      if (existingModel !== newValue) {
        localStorage.setItem('selectedModel', newValue);
      }
    }
  };

  const premiumOptions = useMemo(() => {
    return options.map((option) => {
      const labelStr = typeof option === 'string' ? capitalizeWithUnderscore(option) : capitalize(option.label);
      const valStr = typeof option === 'string' ? option : option.value;
      const isModelSupported = !isProdEnv || prodllms?.includes(valStr);

      return {
        label: labelStr,
        value: valStr,
        description: !isModelSupported ? t('Available in Development Version') : undefined,
        // We can't actually disable individual options in our PremiumDropdown yet,
        // but we add the description to clarify.
      };
    });
  }, [options, isProdEnv]);

  return (
    <div className={view === 'ContentView' ? 'w-[200px]' : 'w-full'} id='llmdropdown'>
      <PremiumDropdown
        value={currentValue}
        options={premiumOptions}
        onChange={handleChange}
        placeholder={placeholder || t('Select an option')}
        icon={<RiRobot3Line />}
        width='100%'
      />
    </div>
  );
};

export default DropdownComponent;
