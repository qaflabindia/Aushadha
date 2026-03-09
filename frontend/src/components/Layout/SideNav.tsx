import React, { useContext } from 'react';
import {
  RiUserSearchLine,
  RiGlobalLine,
  RiRobotLine,
  RiSettings3Line,
} from 'react-icons/ri';
import TooltipWrapper from '../UI/TipWrapper';
import { SideNavProps, DrawerMode } from '../../types';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import { useTranslate } from '../../context/TranslationContext';
import clsx from 'clsx';

const SideNav: React.FC<SideNavProps> = ({
  toggleLeftDrawer,
  toggleRightDrawer,
  activeDrawerMode,
  setActiveDrawerMode,
  isLeftExpanded,
  isRightExpanded,
}) => {
  const { colorMode } = useContext(ThemeWrapperContext);
  const t = useTranslate();

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

  // Helper to render a nav icon button with consistent styling
  const NavIcon: React.FC<{
    tooltip: string;
    onClick: () => void;
    isActive: boolean;
    children: React.ReactNode;
  }> = ({ tooltip, onClick, isActive, children }) => (
    <TooltipWrapper tooltip={tooltip} placement="right">
      <div
        className={clsx(
          'w-12 h-12 rounded-xl cursor-pointer transition-all duration-500 group relative flex items-center justify-center glass-luxe',
          {
            'hover:shadow-[0_0_20px_rgba(255,255,255,0.05)] text-white/40 hover:text-white': colorMode === 'dark' && !isActive,
            'hover:shadow-md text-gray-400 hover:text-blue-600': colorMode === 'light' && !isActive,
            'bg-white/10 text-white': colorMode === 'dark' && isActive,
            'bg-gray-100 text-blue-600': colorMode === 'light' && isActive,
          }
        )}
        onClick={onClick}
      >
        <div className="group-hover:scale-110 transition-transform duration-300">{children}</div>
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
      </div>
    </TooltipWrapper>
  );

  return (
    <div className='flex flex-col h-full items-center py-8 gap-6 overflow-hidden'>

      {/* ── Primary Nav Icons ── */}
      <NavIcon
        tooltip={t('Patient Insights')}
        onClick={() => handleLeftDrawerClick('upload')}
        isActive={isLeftExpanded && activeDrawerMode === 'upload'}
      >
        <RiUserSearchLine size={22} />
      </NavIcon>

      <NavIcon
        tooltip={t('Global Research')}
        onClick={() => handleLeftDrawerClick('research')}
        isActive={isLeftExpanded && activeDrawerMode === 'research'}
      >
        <RiGlobalLine size={22} />
      </NavIcon>

      {/* ── Divider ── */}
      <div className={clsx('w-6 h-[0.5px] opacity-10', {
        'bg-white': colorMode === 'dark',
        'bg-black': colorMode === 'light',
      })} />

      {/* ── AI Assistant (right drawer) ── */}
      <NavIcon
        tooltip={t('AI Assistant')}
        onClick={() => toggleRightDrawer()}
        isActive={isRightExpanded}
      >
        <RiRobotLine size={22} />
      </NavIcon>

      {/* ── Workspace Settings ── */}
      <NavIcon
        tooltip={t('Workspace Settings')}
        onClick={() => handleLeftDrawerClick('settings')}
        isActive={activeDrawerMode === 'settings' && !isLeftExpanded}
      >
        <RiSettings3Line size={22} />
      </NavIcon>

    </div>
  );
};

export default SideNav;
