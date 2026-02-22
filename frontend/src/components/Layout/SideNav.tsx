import React, { useContext } from 'react';
import {
  RiUserSearchLine,
  RiGlobalLine,
  RiRobotLine,
} from 'react-icons/ri';
import TooltipWrapper from '../UI/TipWrapper';
import { SideNavProps } from '../../types';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import clsx from 'clsx';

const SideNav: React.FC<SideNavProps> = ({
  toggleLeftDrawer,
  toggleRightDrawer,
}) => {
  const { colorMode } = useContext(ThemeWrapperContext);

  return (
    <div className='flex flex-col h-full items-center py-8 gap-10 overflow-hidden'>
      {/* Signature Floating Navigation */}
      <TooltipWrapper tooltip="Patient Insights" placement="right">
        <div 
          className={clsx("w-12 h-12 rounded-xl cursor-pointer transition-all duration-500 group relative flex items-center justify-center glass-luxe", {
            'hover:shadow-[0_0_20px_rgba(255,255,255,0.05)] text-white/40 hover:text-white': colorMode === 'dark',
            'hover:shadow-md text-gray-400 hover:text-blue-600': colorMode === 'light',
          })}
          onClick={() => toggleLeftDrawer()}
        >
          <RiUserSearchLine size={22} className="group-hover:scale-110 transition-transform duration-500" />
          <div className={clsx("absolute left-[-12px] w-[3px] h-0 group-hover:h-6 rounded-r-full transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)]", {
            'bg-gradient-to-b from-[#D4AF37] to-[#E5E4E2] shadow-[0_0_15px_rgba(212,175,55,0.4)]': colorMode === 'dark',
            'bg-blue-600': colorMode === 'light',
          })} />
        </div>
      </TooltipWrapper>

      <TooltipWrapper tooltip="Global Research" placement="right">
        <div 
          className={clsx("w-12 h-12 rounded-xl cursor-pointer transition-all duration-500 group relative flex items-center justify-center glass-luxe", {
            'hover:shadow-[0_0_20px_rgba(255,255,255,0.05)] text-white/40 hover:text-white': colorMode === 'dark',
            'hover:shadow-md text-gray-400 hover:text-blue-600': colorMode === 'light',
          })}
          onClick={() => toggleLeftDrawer()}
        >
          <RiGlobalLine size={22} className="group-hover:scale-110 transition-transform duration-500" />
          <div className={clsx("absolute left-[-12px] w-[3px] h-0 group-hover:h-6 rounded-r-full transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)]", {
            'bg-gradient-to-b from-[#D4AF37] to-[#E5E4E2] shadow-[0_0_15px_rgba(212,175,55,0.4)]': colorMode === 'dark',
            'bg-blue-600': colorMode === 'light',
          })} />
        </div>
      </TooltipWrapper>

      <div className={clsx("w-6 h-[0.5px] opacity-10", {
        'bg-white': colorMode === 'dark',
        'bg-black': colorMode === 'light',
      })} />

      <TooltipWrapper tooltip="AI Assistant" placement="right">
        <div 
          className={clsx("w-12 h-12 rounded-xl cursor-pointer transition-all duration-500 group relative flex items-center justify-center glass-luxe", {
            'hover:shadow-[0_0_20px_rgba(255,255,255,0.05)] text-white/40 hover:text-white': colorMode === 'dark',
            'hover:shadow-md text-gray-400 hover:text-blue-600': colorMode === 'light',
          })}
          onClick={() => toggleRightDrawer()}
        >
          <RiRobotLine size={22} className="group-hover:scale-110 transition-transform duration-500" />
          <div className={clsx("absolute left-[-12px] w-[3px] h-0 group-hover:h-6 rounded-r-full transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)]", {
            'bg-gradient-to-b from-[#D4AF37] to-[#E5E4E2] shadow-[0_0_15px_rgba(212,175,55,0.4)]': colorMode === 'dark',
            'bg-blue-600': colorMode === 'light',
          })} />
        </div>
      </TooltipWrapper>
    </div>
  );
};

export default SideNav;
