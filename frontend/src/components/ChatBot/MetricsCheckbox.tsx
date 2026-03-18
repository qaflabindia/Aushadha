import { Checkbox } from '@neo4j-ndl/react';
import { useTranslate } from '../../context/TranslationContext';

function MetricsCheckbox({
  enableReference,
  toggleReferenceVisibility,
  isDisabled = false,
}: {
  enableReference: boolean;
  toggleReferenceVisibility: React.DispatchWithoutAction;
  isDisabled?: boolean;
}) {
  const t = useTranslate();
  return (
    <Checkbox
      isDisabled={isDisabled}
      label={t('getMoreMetrics')}
      isChecked={enableReference}
      onChange={toggleReferenceVisibility}
    />
  );
}
export default MetricsCheckbox;
