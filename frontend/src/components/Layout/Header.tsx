import LuxuryLogo from '../../assets/images/aushadha_luxury_logo.png';
import { MoonIconOutline, SunIconOutline, LockClosedIconOutline } from '@neo4j-ndl/react/icons';
import { Typography } from '@neo4j-ndl/react';
import { memo, useContext, useRef, useState } from 'react';
import clsx from 'clsx';
import { IconButtonWithToolTip } from '../UI/IconButtonToolTip';
import { tooltips } from '../../utils/Constants';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';

import { useMessageContext } from '../../context/UserMessages';
import { RiChatSettingsLine, RiBarChart2Line, RiLayoutMasonryLine } from 'react-icons/ri';
import ChatModeToggle from '../ChatBot/ChatModeToggle';
import { useGoogleAuth } from '../../context/GoogleAuthContext';
import { HeaderProp } from '../../types';
import Profile from '../User/Profile';
import SecretVaultModal from '../Popups/SecretVaultModal';
import LanguageSelector from '../UI/LanguageSelector';
import TooltipWrapper from '../UI/TipWrapper';
import { useTranslation } from '../../context/LanguageContext';

const Header: React.FC<HeaderProp> = ({ deleteOnClick: _deleteOnClick, showBackButton: _showBackButton }) => {
  const { colorMode, toggleColorMode } = useContext(ThemeWrapperContext);

  const { messages: _messages } = useMessageContext();
  const chatAnchor = useRef<HTMLDivElement>(null);
  const [showChatModeOption, setShowChatModeOption] = useState<boolean>(false);
  const [showSecretVault, setShowSecretVault] = useState<boolean>(false);
  const t = useTranslation();
  const { user } = useGoogleAuth();

  return (
    <div className='flex items-center justify-between h-full px-8'>
      {/* Precision Brand Block */}
      <section className='flex items-center gap-6'>
        <div className='flex items-center gap-4'>
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
              AUSHADHA
            </Typography>
            <Typography
              variant='body-small'
              className={clsx('!m-0 transition-colors opacity-60 tracking-concierge text-[7px]', {
                'text-[#D4AF37]': colorMode === 'dark',
                'text-gray-500': colorMode === 'light',
              })}
            >
              Medical Intelligence
            </Typography>
          </div>
        </div>
      </section>

      {/* Global Interface Controls */}
      <section className='flex items-center gap-8'>
        {/* Glass Search Trigger with Gold/Silver Typography */}
        {(user?.role === 'Doctor' || user?.role === 'Staff' || user?.role === 'Admin') && (
          <div
            ref={chatAnchor}
            onClick={() => setShowChatModeOption(true)}
            className={clsx(
              'flex items-center gap-3 px-5 py-2 rounded-full border transition-all cursor-pointer group glass-luxe',
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
              Intelligence Search
            </span>
          </div>
        )}

        <div className='flex items-center gap-6'>
          <TooltipWrapper tooltip={t('dataInsights')} placement='bottom'>
            <div className='cursor-pointer transition-opacity hover:opacity-100 opacity-40'>
              <RiBarChart2Line size={20} className={colorMode === 'dark' ? 'text-white' : 'text-gray-700'} />
            </div>
          </TooltipWrapper>

          <TooltipWrapper tooltip={t('knowledgeGraph')} placement='bottom'>
            <div className='cursor-pointer transition-opacity hover:opacity-100 opacity-40'>
              <RiLayoutMasonryLine size={20} className={colorMode === 'dark' ? 'text-white' : 'text-gray-700'} />
            </div>
          </TooltipWrapper>

          <LanguageSelector />

          <IconButtonWithToolTip
            label={tooltips.theme}
            clean
            text={tooltips.theme}
            onClick={toggleColorMode}
            className='hover:rotate-12 transition-transform opacity-60 hover:opacity-100'
          >
            {colorMode === 'dark' ? (
              <SunIconOutline className='w-5 h-5 text-white' />
            ) : (
              <MoonIconOutline className='w-5 h-5 text-gray-700' />
            )}
          </IconButtonWithToolTip>

          <TooltipWrapper tooltip='Secret Vault' placement='bottom'>
            {user?.role === 'Admin' && (
              <div
                onClick={() => setShowSecretVault(true)}
                className={clsx('cursor-pointer transition-all hover:text-[#D4AF37] opacity-60 hover:opacity-100', {
                  'text-white': colorMode === 'dark',
                  'text-gray-400': colorMode === 'light',
                })}
              >
                <LockClosedIconOutline className='w-5 h-5' />
              </div>
            )}
          </TooltipWrapper>

          <Profile />
        </div>
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
      <SecretVaultModal open={showSecretVault} onClose={() => setShowSecretVault(false)} />
    </div>
  );
};

export default memo(Header);
