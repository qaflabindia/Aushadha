import { Flex, IconButton } from '@neo4j-ndl/react';
import { RiArrowLeftSLine, RiArrowRightSLine } from 'react-icons/ri';
import TipWrapper from '../UI/TipWrapper';
import { chatModeReadableLables } from '../../utils/Constants';
import { useTranslation } from '../../hooks/useTranslation';

export default function ChatModesSwitch({
  switchToOtherMode,
  currentModeIndex,
  modescount,
  currentMode,
  isFullScreen,
}: {
  switchToOtherMode: (index: number) => void;
  currentModeIndex: number;
  modescount: number;
  currentMode: string;
  isFullScreen: boolean;
}) {
  const t = useTranslation();
  const chatmodetoshow = t(chatModeReadableLables[currentMode] as any);
  return (
    <Flex flexDirection='row' gap='1' alignItems='center'>
      <IconButton
        isDisabled={currentModeIndex === 0}
        size='small'
        isClean={true}
        onClick={() => switchToOtherMode(currentModeIndex - 1)}
        ariaLabel='left'
      >
        <RiArrowLeftSLine className='n-size-token-4' size={16} />
      </IconButton>
      <TipWrapper tooltip={chatmodetoshow} placement='top'>
        <div
          className={`n-body-medium  ${!isFullScreen ? 'max-w-[50px] text-ellipsis text-nowrap overflow-hidden' : ''}`}
        >
          {chatmodetoshow}
        </div>
      </TipWrapper>
      <IconButton
        isDisabled={currentModeIndex === modescount - 1}
        size='small'
        isClean={true}
        onClick={() => switchToOtherMode(currentModeIndex + 1)}
        ariaLabel='right'
      >
        <RiArrowRightSLine className='n-size-token-4' size={16} />
      </IconButton>
    </Flex>
  );
}
