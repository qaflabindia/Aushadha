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
      {/* Compact action row shown in the chat header */}
      <div
        className={clsx('flex items-center gap-0.5 transition-colors duration-500', {
          'text-[#D4AF37]/80': colorMode === 'dark',
          'text-[#5C4A1E]/80': colorMode === 'light',
        })}
      >
        <IconButtonWithToolTip text={t('Close')} onClick={closeChatBot} clean placement='bottom' label={t('Close')}>
          <RiCloseLine className='n-size-token-5 outline-none' size={18} />
        </IconButtonWithToolTip>

        <IconButtonWithToolTip
          text={t('Delete Chat')}
          clean
          onClick={deleteOnClick}
          disabled={messages.length <= 1}
          placement='bottom'
          label={t('Delete Chat')}
        >
          <RiDeleteBin6Line
            className={clsx('n-size-token-5 outline-none', messages.length <= 1 ? 'opacity-50' : 'text-red-500')}
            size={18}
          />
        </IconButtonWithToolTip>

        {toggleFullScreen && (
          <IconButtonWithToolTip
            text={isFullScreen ? t('Minimise') : t('Maximise')}
            onClick={toggleFullScreen}
            clean
            placement='bottom'
            label={isFullScreen ? t('Minimise') : t('Maximise')}
          >
            {isFullScreen ? (
              <RiCollapseDiagonalLine className='n-size-token-5 outline-none' size={18} />
            ) : (
              <RiExpandDiagonalLine className='n-size-token-5 outline-none' size={18} />
            )}
          </IconButtonWithToolTip>
        )}

        <IconButtonWithToolTip
          text={t('Download Conversation')}
          onClick={() => downloadClickHandler({ conversation: messages }, downloadLinkRef as any, 'aushadha-chat.json')}
          clean
          placement='bottom'
          label={t('Download Conversation')}
        >
          <RiDownloadLine className='n-size-token-5 outline-none' size={18} />
        </IconButtonWithToolTip>
      </div>
    </>
  );
};

export default memo(ExpandedChatButtonContainer);
