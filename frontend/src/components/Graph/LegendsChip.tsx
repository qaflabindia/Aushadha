import { LegendChipProps } from '../../types';
import Legend from '../UI/Legend';
import { useTranslate } from '../../context/TranslationContext';

export const LegendsChip: React.FunctionComponent<LegendChipProps> = ({ scheme, label, type, count, onClick }) => {
  const t = useTranslate();
  const title = label === '__Community__' ? t('communities') : t(label);
  return (
    <Legend
      title={title}
      {...(count !== undefined && { count })}
      bgColor={scheme[label]}
      type={type}
      onClick={onClick}
    />
  );
};
