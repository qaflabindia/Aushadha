import React from 'react';
import Header from './Header';
import SideNav from './SideNav';
import { useContext } from 'react';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import clsx from 'clsx';

import { DrawerMode } from '../../types';

interface DashboardScaffoldProps {
  children: React.ReactNode;
  isLeftExpanded: boolean;
  isRightExpanded: boolean;
  toggleLeftDrawer: () => void;
  toggleRightDrawer: () => void;
  deleteOnClick: () => void;
  showBackButton?: boolean;
  activeDrawerMode: DrawerMode;
  setActiveDrawerMode: (mode: DrawerMode) => void;
}

const DashboardScaffold: React.FC<DashboardScaffoldProps> = ({ 
  children, 
  isLeftExpanded, 
  isRightExpanded,
  toggleLeftDrawer,
  toggleRightDrawer,
  deleteOnClick,
  activeDrawerMode,
  setActiveDrawerMode,
}) => {
  const { colorMode } = useContext(ThemeWrapperContext);

  return (
    <div className={clsx("flex h-screen w-screen overflow-hidden transition-all duration-700 font-['Inter']", {
      'bg-[#030303] text-[#E5E4E2]': colorMode === 'dark',
      'bg-[#F2F2F2] text-[#1A1A1A]': colorMode === 'light',
    })}>
      {/* Precision Ambient Glows - Deepened Architecture */}
      {colorMode === 'dark' && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
          <div className="absolute top-[-20%] right-[-15%] w-[70%] h-[70%] bg-[#D4AF37]/8 blur-[140px] rounded-full animate-pulse duration-7000" />
          <div className="absolute bottom-[-15%] left-[-10%] w-[50%] h-[50%] bg-[#E5E4E2]/4 blur-[120px] rounded-full opacity-30" />
          <div className="absolute top-[20%] left-[10%] w-[30%] h-[30%] bg-[#D4AF37]/3 blur-[100px] rounded-full animate-pulse duration-5000" />
        </div>
      )}

      {/* Main Glass Shell */}
      <div className="flex-1 flex flex-col relative z-10 transition-all duration-500">
        
        {/* Precision Title Bar (Glass Overlay) */}
        <header className={clsx("h-16 z-30 flex items-center glass-luxe transition-all duration-300", {
          'border-b border-white/5': colorMode === 'dark',
          'border-b border-gray-200': colorMode === 'light',
        })}>
          <Header deleteOnClick={deleteOnClick} hidePatientDropdown={activeDrawerMode === 'admin'} />
        </header>

        {/* Workspace Body */}
        <div className="flex flex-1 overflow-hidden">
          {/* Side Navigation Pane (40px Blur) */}
          <aside className={clsx("w-[72px] z-20 flex flex-col items-center glass-luxe transition-all duration-500", {
             'border-r border-white/5': colorMode === 'dark',
             'border-r border-gray-100': colorMode === 'light',
          })}>
             <SideNav 
                toggleLeftDrawer={toggleLeftDrawer}
                toggleRightDrawer={toggleRightDrawer}
                isLeftExpanded={isLeftExpanded}
                isRightExpanded={isRightExpanded}
                activeDrawerMode={activeDrawerMode}
                setActiveDrawerMode={setActiveDrawerMode}
              />
          </aside>

          {/* Core Content Area - Crystalline or Smoked Glass */}
          <main className={clsx("flex-1 flex flex-col overflow-hidden relative z-10 p-4 transition-all duration-500", {
            'bg-black/10': colorMode === 'dark',
            'bg-white/40': colorMode === 'light',
          })}>
            <div className="flex-1 flex flex-col glass-luxe border-grad-gs rounded-[20px] overflow-hidden shadow-2xl">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};

export default DashboardScaffold;
