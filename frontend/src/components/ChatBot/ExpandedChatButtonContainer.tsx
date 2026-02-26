import {
  TrashIconOutline,
  ChevronRightIconOutline,
  ArrowsPointingOutIconSolid,
  ArrowsPointingInIconSolid,
  ArrowDownTrayIconOutline,
} from '@neo4j-ndl/react/icons';

import { Messages } from '../../types';
import { IconButtonWithToolTip } from '../UI/IconButtonToolTip';
import { tooltips } from '../../utils/Constants';
import { memo, useRef, useContext } from 'react';
import clsx from 'clsx';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import { downloadClickHandler } from '../../utils/Utils';

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
        <IconButtonWithToolTip text='Close' onClick={closeChatBot} clean placement='left' label='Close'>
          <ChevronRightIconOutline className='w-7 h-7 outline-none' />
        </IconButtonWithToolTip>

        <IconButtonWithToolTip
          text={tooltips.clearChat}
          aria-label='Remove chat history'
          clean
          onClick={deleteOnClick}
          disabled={messages.length <= 1}
          placement='left'
          label={tooltips.clearChat}
        >
          <TrashIconOutline
            className={clsx('w-7 h-7 outline-none', messages.length <= 1 ? 'opacity-50' : 'text-red-500')}
          />
        </IconButtonWithToolTip>

        {toggleFullScreen && (
          <IconButtonWithToolTip
            text={isFullScreen ? 'Collapse Screen' : 'Expand Screen'}
            onClick={toggleFullScreen}
            clean
            placement='left'
            label='Toggle Fullscreen'
          >
            {isFullScreen ? (
              <ArrowsPointingInIconSolid className='w-7 h-7 outline-none' />
            ) : (
              <ArrowsPointingOutIconSolid className='w-7 h-7 outline-none' />
            )}
          </IconButtonWithToolTip>
        )}

        <IconButtonWithToolTip
          text='Download Chat'
          onClick={() => downloadClickHandler({ conversation: messages }, downloadLinkRef as any, 'aushadha-chat.json')}
          clean
          placement='left'
          label='Download'
        >
          <ArrowDownTrayIconOutline className='w-7 h-7 outline-none' />
        </IconButtonWithToolTip>
      </div>
    </>
  );
};

export default memo(ExpandedChatButtonContainer);
