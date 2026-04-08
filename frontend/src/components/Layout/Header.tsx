import LuxuryLogo from '../../assets/images/aushadha_luxury_logo.png';
import { Typography } from '@neo4j-ndl/react';
import { memo, useContext, useRef, useState } from 'react';
import clsx from 'clsx';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import { useMessageContext } from '../../context/UserMessages';
import { RiChatSettingsLine } from 'react-icons/ri';
import ChatModeToggle from '../ChatBot/ChatModeToggle';
import { useGoogleAuth } from '../../context/GoogleAuthContext';
import { HeaderProp } from '../../types';
import { Avatar } from '@neo4j-ndl/react';
import TooltipWrapper from '../UI/TipWrapper';
import { useTranslate } from '../../context/TranslationContext';
import { usePatientContext } from '../../context/PatientContext';

const Header: React.FC<HeaderProp> = ({ deleteOnClick: _deleteOnClick }) => {
  const { colorMode } = useContext(ThemeWrapperContext);

  const { messages: _messages } = useMessageContext();
  const chatAnchor = useRef<HTMLDivElement>(null);
  const [showChatModeOption, setShowChatModeOption] = useState<boolean>(false);
  const t = useTranslate();
  const { user } = useGoogleAuth();
  const { selectedPatient } = usePatientContext();

  return (
    <div className='flex items-center justify-between h-full px-6'>
      {/* ── Brand Block ── */}
      <section className='flex items-center gap-4'>
        <div className='relative p-0.5 rounded-full border border-white/5 bg-white/5 transition-all duration-500'>
          <img src={LuxuryLogo} className='h-8 w-8 rounded-full' alt='Logo' />
        </div>
        <div className='flex flex-col'>
          <Typography
            variant='h5'
            className={clsx('!m-0 transition-colors tracking-brand', {
              'text-white': colorMode === 'dark',
              'text-[#1A1A1A]': colorMode === 'light',
            })}
          >
            {t('AYUSHPRAGYA')}
          </Typography>
          <Typography
            variant='body-small'
            className={clsx('!m-0 transition-colors opacity-60 tracking-concierge text-[7px]', {
              'text-[#D4AF37]': colorMode === 'dark',
              'text-gray-500': colorMode === 'light',
            })}
          >
            {t('Medical Intelligence')}
          </Typography>
        </div>
      </section>

      {/* ── Right Controls ── */}
      <section className='flex items-center gap-5'>
        {/* Patient Context Display */}
        {(user?.role === 'Doctor' || user?.role === 'Staff' || user?.role === 'Admin') && (
          <div
            className={clsx(
              'flex items-center gap-2 px-3 py-1 rounded-full border transition-all glass-luxe text-[10px] font-bold tracking-tight',
              {
                'border-[#D4AF37]/30 text-[#D4AF37] bg-[#D4AF37]/5 shadow-[0_0_15px_rgba(212,175,55,0.05)]':
                  colorMode === 'dark' && selectedPatient,
                'border-blue-200 text-blue-600 bg-blue-50': colorMode === 'light' && selectedPatient,
                'border-white/5 text-white/30': colorMode === 'dark' && !selectedPatient,
                'border-gray-100 text-gray-400': colorMode === 'light' && !selectedPatient,
              }
            )}
          >
            {selectedPatient ? (
              <>
                <span className='opacity-60 uppercase tracking-[0.1em]'>{t('Active Patient')}:</span>
                <span className='text-[11px]'>{selectedPatient.case_id}</span>
              </>
            ) : (
              <span className='italic opacity-40 italic'>{t('Context: Not Selected')}</span>
            )}
          </div>
        )}

        {/* Intelligence Search / Chat Mode Trigger — non-Patients only */}
        {(user?.role === 'Doctor' || user?.role === 'Staff' || user?.role === 'Admin') && (
          <div
            ref={chatAnchor}
            onClick={() => setShowChatModeOption(true)}
            className={clsx(
              'flex items-center gap-3 px-4 py-1.5 rounded-full border transition-all cursor-pointer group glass-luxe',
              {
                'border-white/10 shadow-[0_0_20px_rgba(212,175,55,0.1)]': colorMode === 'dark',
                'border-gray-200': colorMode === 'light',
              }
            )}
          >
            <RiChatSettingsLine
              className={clsx('text-sm transition-colors', {
                'text-[#D4AF37]': colorMode === 'dark',
                'text-gray-500': colorMode === 'light',
              })}
            />
            <span
              className={clsx('text-[10px] uppercase tracking-[0.25em] font-extrabold transition-all', {
                'bg-gradient-to-r from-white via-[#D4AF37] to-white bg-clip-text text-transparent group-hover:via-white group-hover:to-[#D4AF37]':
                  colorMode === 'dark',
                'text-[#1A1A1A] group-hover:text-gray-600': colorMode === 'light',
              })}
            >
              {t('Intelligence Search')}
            </span>
          </div>
        )}

        {/* Active User Avatar */}

        {/* Active User Avatar */}
        {user && (
          <TooltipWrapper
            tooltip={`${user.name ?? user.email} · ${user.role ?? 'User'} — ${t('Open Settings for full profile')}`}
            placement='bottom'
          >
            <Avatar name={user.name ?? user.email} source={user.picture ?? undefined} size='small' />
          </TooltipWrapper>
        )}
      </section>

      <ChatModeToggle
        closeHandler={(_, reason) => {
          if (reason.type === 'backdropClick') {
            setShowChatModeOption(false);
          }
        }}
        open={showChatModeOption}
        menuAnchor={chatAnchor}
        isRoot={false}
      />
    </div>
  );
};

export default memo(Header);
