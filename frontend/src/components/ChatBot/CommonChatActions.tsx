import { ClipboardDocumentIconOutline, SpeakerWaveIconOutline, SpeakerXMarkIconOutline } from '@neo4j-ndl/react/icons';
import { Messages } from '../../types';
import ButtonWithToolTip from '../UI/ButtonWithToolTip';
import { IconButtonWithToolTip } from '../UI/IconButtonToolTip';
import { buttonCaptions, tooltips } from '../../utils/Constants';
import { useContext } from 'react';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import clsx from 'clsx';

export default function CommonActions({
  chat,
  detailsHandler,
  speechHandler,
  copyHandler,
  listMessages,
  activeChat,
}: {
  chat: Messages;
  activeChat: Messages | null;
  detailsHandler: (chat: Messages, activeChat: Messages | null) => void;
  speechHandler: (chat: Messages) => void;
  copyHandler: (message: string, id: number) => void;
  listMessages: Messages[];
}) {
  const { colorMode } = useContext(ThemeWrapperContext);

  return (
    <div className='flex items-center gap-2'>
      <ButtonWithToolTip
        className={clsx(
          'px-4 py-1.5 h-auto rounded-xl text-[10px] uppercase font-extrabold tracking-widest transition-all duration-300 backdrop-blur-md',
          {
            'bg-[#D4AF37] !text-black border border-[#D4AF37]/30 hover:bg-[#C5A028] hover:shadow-[0_0_15px_rgba(212,175,55,0.4)]':
              colorMode === 'dark',
            'bg-blue-50/80 !text-blue-600 border border-blue-200 hover:bg-blue-100': colorMode === 'light',
          }
        )}
        fill='text'
        placement='top'
        clean
        text='Retrieval Information'
        label='Retrieval Information'
        disabled={chat.isTyping || chat.isLoading}
        onClick={() => detailsHandler(chat, activeChat)}
        aria-label='Retrieval Information'
      >
        {buttonCaptions.details}
      </ButtonWithToolTip>
      <IconButtonWithToolTip
        label='copy text'
        placement='top'
        clean
        text={chat.copying ? tooltips.copied : tooltips.copy}
        onClick={() => copyHandler(chat.modes[chat.currentMode]?.message, chat.id)}
        disabled={chat.isTyping || chat.isLoading}
        aria-label='copy text'
      >
        <ClipboardDocumentIconOutline className='n-size-token-4' />
      </IconButtonWithToolTip>
      <IconButtonWithToolTip
        placement='top'
        clean
        onClick={() => speechHandler(chat)}
        text={chat.speaking ? tooltips.stopSpeaking : tooltips.textTospeech}
        disabled={listMessages.some((msg) => msg.speaking && msg.id !== chat.id)}
        label={chat.speaking ? 'stop speaking' : 'text to speech'}
        aria-label='speech'
      >
        {chat.speaking ? (
          <SpeakerXMarkIconOutline className='n-size-token-4' />
        ) : (
          <SpeakerWaveIconOutline className='n-size-token-4' />
        )}
      </IconButtonWithToolTip>
    </div>
  );
}
