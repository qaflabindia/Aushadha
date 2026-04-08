import { Flex, IconButton, Popover, Typography } from '@neo4j-ndl/react';
import { RiInformationLine } from 'react-icons/ri';
import { useTranslate } from '../../context/TranslationContext';

export default function NotAvailableMetric() {
  const t = useTranslate();
  return (
    <Flex flexDirection='row' alignItems='center'>
      <span>{t('notAvailable')}</span>
      <Popover placement='top-middle-bottom-middle' hasAnchorPortal={true}>
        <Popover.Trigger hasButtonWrapper>
          <IconButton size='small' isClean ariaLabel='infoicon'>
            <RiInformationLine size={16} />
          </IconButton>
        </Popover.Trigger>
        <Popover.Content className='p-2'>
          <Typography variant='body-small'>{t('geminiMetricsWarning')}</Typography>
        </Popover.Content>
      </Popover>
    </Flex>
  );
}
