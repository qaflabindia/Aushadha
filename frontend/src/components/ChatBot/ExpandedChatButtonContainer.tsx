import {
  RiCloseLine,
  RiDeleteBin6Line,
  RiExpandDiagonalLine,
  RiCollapseDiagonalLine,
  RiDownloadLine,
} from 'react-icons/ri';

import { Messages } from '../../types';
import { IconButtonWithToolTip } from '../UI/IconButtonToolTip';
import { memo, useRef, useContext } from 'react';
import clsx from 'clsx';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import { downloadClickHandler } from '../../utils/Utils';
import { useTranslation } from '../../hooks/useTranslation';

export interface ExpandedChatButtonProps {
  closeChatBot: () => void;
  deleteOnClick: () => void;
  messages: Messages[];
  isFullScreen?: boolean;
  toggleFullScreen?: () => void;
}

const ExpandedChatButtonContainer: React.FC<ExpandedChatButtonProps> = ({
  closeChatBot,
  deleteOnClick,
  messages,
  isFullScreen,
  toggleFullScreen,
}) => {
  const t = useTranslation();
  const downloadLinkRef = useRef<HTMLAnchorElement>(null);
  const { colorMode } = useContext(ThemeWrapperContext);

  return (
    <>
      <a ref={downloadLinkRef} className='hidden' />
      <div
        className={clsx(
          'w-14 min-w-[56px] flex flex-col items-center py-4 gap-4 transition-all duration-700 glass-luxe z-30',
          {
            'bg-[#080808]/60 border-l border-white/10': colorMode === 'dark',
            'bg-white/60 border-l border-gray-200': colorMode === 'light',
          }
        )}
      >
        <IconButtonWithToolTip text={t('Close')} onClick={closeChatBot} clean placement='right' label={t('Close')}>
          <RiCloseLine className='n-size-token-7 outline-none' size={28} />
        </IconButtonWithToolTip>

        <IconButtonWithToolTip
          text={t('Delete Chat')}
          clean
          onClick={deleteOnClick}
          disabled={messages.length <= 1}
          placement='right'
          label={t('Delete Chat')}
        >
          <RiDeleteBin6Line
            className={clsx('n-size-token-7 outline-none', messages.length <= 1 ? 'opacity-50' : 'text-red-500')}
            size={28}
          />
        </IconButtonWithToolTip>

        {toggleFullScreen && (
          <IconButtonWithToolTip
            text={isFullScreen ? t('Minimise') : t('Maximise')}
            onClick={toggleFullScreen}
            clean
            placement='right'
            label={isFullScreen ? t('Minimise') : t('Maximise')}
          >
            {isFullScreen ? (
              <RiCollapseDiagonalLine className='n-size-token-7 outline-none' size={28} />
            ) : (
              <RiExpandDiagonalLine className='n-size-token-7 outline-none' size={28} />
            )}
          </IconButtonWithToolTip>
        )}

        <IconButtonWithToolTip
          text={t('Download Conversation')}
          onClick={() => downloadClickHandler({ conversation: messages }, downloadLinkRef as any, 'aushadha-chat.json')}
          clean
          placement='right'
          label={t('Download Conversation')}
        >
          <RiDownloadLine className='n-size-token-7 outline-none' size={28} />
        </IconButtonWithToolTip>
      </div>
    </>
  );
};

export default memo(ExpandedChatButtonContainer);
