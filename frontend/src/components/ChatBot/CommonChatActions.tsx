import { RiFileCopyLine, RiVolumeUpLine, RiVolumeMuteLine } from 'react-icons/ri';
import { Messages } from '../../types';
import ButtonWithToolTip from '../UI/ButtonWithToolTip';
import { IconButtonWithToolTip } from '../UI/IconButtonToolTip';
import { useContext } from 'react';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import clsx from 'clsx';
import { useTranslation } from '../../hooks/useTranslation';

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
  const t = useTranslation();

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
        text={t('Retrieval Information')}
        label={t('Retrieval Information')}
        disabled={chat.isTyping || chat.isLoading}
        onClick={() => detailsHandler(chat, activeChat)}
        aria-label={t('Retrieval Information')}
      >
        {t('Details')}
      </ButtonWithToolTip>
      <IconButtonWithToolTip
        label={t('Copy to Clipboard')}
        placement='top'
        clean
        text={chat.copying ? t('Copied') : t('Copy to Clipboard')}
        onClick={() => copyHandler(chat.modes[chat.currentMode]?.message, chat.id)}
        disabled={chat.isTyping || chat.isLoading}
        aria-label={t('Copy to Clipboard')}
      >
        <RiFileCopyLine className='n-size-token-4' size={16} />
      </IconButtonWithToolTip>
      <IconButtonWithToolTip
        placement='top'
        clean
        onClick={() => speechHandler(chat)}
        text={chat.speaking ? t('Stop Speaking') : t('Text to Speech')}
        disabled={listMessages.some((msg) => msg.speaking && msg.id !== chat.id)}
        label={chat.speaking ? t('Stop Speaking') : t('Text to Speech')}
        aria-label='speech'
      >
        {chat.speaking ? (
          <RiVolumeMuteLine className='n-size-token-4' size={16} />
        ) : (
          <RiVolumeUpLine className='n-size-token-4' size={16} />
        )}
      </IconButtonWithToolTip>
    </div>
  );
}
