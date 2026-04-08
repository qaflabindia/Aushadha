import { Checkbox } from '@neo4j-ndl/react';
import React from 'react';
import { CheckboxSectionProps } from '../../types';
import { useTranslate } from '../../context/TranslationContext';

const CheckboxSelection: React.FC<CheckboxSectionProps> = ({
  graphType,
  loading,
  handleChange,
  isCommunity,
  isDocChunk,
  isEntity,
}) => {
  const t = useTranslate();
  return (
    <div className='flex gap-5 mt-2 justify-between'>
      <div className='flex gap-5'>
        {isDocChunk && (
          <Checkbox
            isChecked={graphType.includes('DocumentChunk')}
            label={t('documentChunk')}
            isDisabled={loading}
            onChange={() => handleChange('DocumentChunk')}
          />
        )}
        {isEntity && (
          <Checkbox
            isChecked={graphType.includes('Entities')}
            label={t('entities')}
            isDisabled={loading}
            onChange={() => handleChange('Entities')}
          />
        )}
        {isCommunity && (
          <Checkbox
            isChecked={graphType.includes('Communities')}
            label={t('communities')}
            isDisabled={loading}
            onChange={() => handleChange('Communities')}
          />
        )}
      </div>
    </div>
  );
};
export default CheckboxSelection;
