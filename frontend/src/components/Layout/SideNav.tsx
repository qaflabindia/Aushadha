import React, { useContext } from 'react';
import { IconButton } from '@neo4j-ndl/react';
import { RiUserSearchLine, RiGlobalLine, RiRobotLine, RiSettings3Line } from 'react-icons/ri';
import TooltipWrapper from '../UI/TipWrapper';
import { SideNavProps, DrawerMode } from '../../types';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import { useTranslation } from '../../hooks/useTranslation';
import clsx from 'clsx';
import { useGoogleAuth } from '../../context/GoogleAuthContext';

// ─── NavIcon extracted as a top-level component ──────────────────────────────
// IMPORTANT: This MUST be defined outside SideNav to prevent React from
// treating it as a new component type on every render, which would unmount/remount
// the Tooltip and cause icons to disappear during translation cache updates.
const NavIcon: React.FC<{
  tooltip: string;
  onClick: () => void;
  isActive: boolean;
  colorMode: 'dark' | 'light';
  children: React.ReactNode;
}> = ({ tooltip, onClick, isActive, colorMode, children }) => (
  <TooltipWrapper tooltip={tooltip} placement='right'>
    <IconButton
      ariaLabel={tooltip}
      size='large'
      isClean
      className={clsx(
        'w-12 h-12 rounded-xl transition-all duration-500 group relative flex items-center justify-center glass-luxe',
        {
          'text-white/40 hover:text-white': colorMode === 'dark' && !isActive,
          'text-gray-400 hover:text-blue-600': colorMode === 'light' && !isActive,
          'bg-white/10 text-white': colorMode === 'dark' && isActive,
          'bg-gray-100 text-blue-600': colorMode === 'light' && isActive,
        }
      )}
      onClick={onClick}
    >
      <div className='group-hover:scale-110 transition-transform duration-300'>{children}</div>
      <div
        className={clsx(
          'absolute left-[-12px] w-[3px] rounded-r-full transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)]',
          {
            'bg-gradient-to-b from-[#D4AF37] to-[#E5E4E2] shadow-[0_0_15px_rgba(212,175,55,0.4)]': colorMode === 'dark',
            'bg-blue-600': colorMode === 'light',
            'h-6': isActive,
            'h-0 group-hover:h-6': !isActive,
          }
        )}
      />
    </IconButton>
  </TooltipWrapper>
);

const SideNav: React.FC<SideNavProps> = ({
  toggleLeftDrawer,
  activeDrawerMode,
  setActiveDrawerMode,
  isLeftExpanded,
}) => {
  const { colorMode } = useContext(ThemeWrapperContext);
  const t = useTranslation();
  const { user } = useGoogleAuth();
  const isPatient = user?.role?.toUpperCase() === 'PATIENT';

  // Handles left drawer icons (drawers that expand the left panel OR full-page views)
  const handleLeftDrawerClick = (mode: DrawerMode) => {
    // 'admin' and 'settings' are full-page views, not left-drawer overlays
    if (mode === 'admin' || mode === 'settings') {
      setActiveDrawerMode(mode);
      if (isLeftExpanded) {
        toggleLeftDrawer();
      }
      return;
    }

    // Logic for overlay drawers: 'upload', 'research'
    if (isLeftExpanded && activeDrawerMode === mode) {
      toggleLeftDrawer();
    } else {
      setActiveDrawerMode(mode);
      if (!isLeftExpanded) {
        toggleLeftDrawer();
      }
    }
  };

  return (
    <div className='flex flex-col h-full items-center py-8 gap-6 overflow-hidden'>
      {/* ── Patient Insights / Upload — hidden for Patients ── */}
      {!isPatient && (
        <NavIcon
          tooltip={t('Patient Insights')}
          onClick={() => handleLeftDrawerClick('upload')}
          isActive={isLeftExpanded && activeDrawerMode === 'upload'}
          colorMode={colorMode}
        >
          <RiUserSearchLine size={22} />
        </NavIcon>
      )}

      {/* ── Global Research — hidden for Patients ── */}
      {!isPatient && (
        <NavIcon
          tooltip={t('Global Research')}
          onClick={() => handleLeftDrawerClick('research')}
          isActive={isLeftExpanded && activeDrawerMode === 'research'}
          colorMode={colorMode}
        >
          <RiGlobalLine size={22} />
        </NavIcon>
      )}

      {/* ── Divider — hidden for Patients ── */}
      {!isPatient && (
        <div
          className={clsx('w-6 h-[0.5px] opacity-10', {
            'bg-white': colorMode === 'dark',
            'bg-black': colorMode === 'light',
          })}
        />
      )}

      {/* ── AI Assistant (right drawer) — always visible ── */}
      <NavIcon
        tooltip={t('AI Assistant')}
        onClick={() => handleLeftDrawerClick('chat')}
        isActive={isLeftExpanded && activeDrawerMode === 'chat'}
        colorMode={colorMode}
      >
        <RiRobotLine size={22} />
      </NavIcon>

      {/* ── Settings / Workspace — visible for all (filtered contents for Patients) ── */}
      <NavIcon
        tooltip={isPatient ? t('Settings / Account') : t('Workspace Settings')}
        onClick={() => handleLeftDrawerClick('settings')}
        isActive={activeDrawerMode === 'settings' && !isLeftExpanded}
        colorMode={colorMode}
      >
        <RiSettings3Line size={22} />
      </NavIcon>
    </div>
  );
};

export default SideNav;
