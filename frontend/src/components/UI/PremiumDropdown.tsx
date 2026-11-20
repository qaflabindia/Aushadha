import React, { useState, useRef, useEffect, useContext, useCallback } from 'react';
import { createPortal } from 'react-dom';
import clsx from 'clsx';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import { RiArrowDownSLine, RiCheckLine } from 'react-icons/ri';
import { useTranslate } from '../../context/TranslationContext';

export interface DropdownOption {
  label: string;
  value: string;
  description?: string;
  icon?: React.ReactNode;
}

interface PremiumDropdownProps {
  value: string | null;
  options: DropdownOption[];
  onChange: (value: string) => void;
  placeholder?: string;
  icon?: React.ReactNode;
  disabled?: boolean;
  className?: string;
  width?: string;
}

export const PremiumDropdown: React.FC<PremiumDropdownProps> = ({
  value,
  options,
  onChange,
  placeholder = 'Select...',
  icon,
  disabled = false,
  className = '',
  width = '100%',
}) => {
  const { colorMode } = useContext(ThemeWrapperContext);
  const t = useTranslate();
  const [isOpen, setIsOpen] = useState(false);
  const [dropUp, setDropUp] = useState(false);
  const [panelPos, setPanelPos] = useState<{ left: number; width: number; top?: number; bottom?: number }>({
    left: 0,
    width: 0,
  });
  const menuRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find((opt) => opt.value === value);

  // The panel is rendered at the end of <body> so it sits above every glass panel and
  // gets its own backdrop blur; position it against the trigger in viewport coordinates.
  const placePanel = useCallback(() => {
    if (!menuRef.current) {
      return;
    }
    const rect = menuRef.current.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    // If the trigger is in the bottom 40% of the screen, open upwards
    const up = rect.bottom > viewportHeight * 0.6;
    setDropUp(up);
    setPanelPos(
      up
        ? { left: rect.left, width: rect.width, bottom: viewportHeight - rect.top + 8 }
        : { left: rect.left, width: rect.width, top: rect.bottom + 8 }
    );
  }, []);

  React.useLayoutEffect(() => {
    if (!isOpen) {
      return;
    }
    placePanel();
    window.addEventListener('resize', placePanel);
    window.addEventListener('scroll', placePanel, true);
    return () => {
      window.removeEventListener('resize', placePanel);
      window.removeEventListener('scroll', placePanel, true);
    };
  }, [isOpen, placePanel]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (menuRef.current?.contains(target) || panelRef.current?.contains(target)) {
        return;
      }
      setIsOpen(false);
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, []);

  return (
    <div className={clsx('relative', className)} ref={menuRef} style={{ width }}>
      <button
        type='button'
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'w-full flex items-center justify-between px-4 py-2.5 rounded-xl border transition-all duration-300 text-sm group',
          {
            'opacity-50 cursor-not-allowed': disabled,
            // Dark Mode Glass
            '!bg-black/70 !backdrop-blur-2xl border-white/20 text-white hover:border-[#D4AF37]/50 hover:shadow-[0_0_20px_rgba(212,175,55,0.1)]':
              colorMode === 'dark' && !disabled,
            'border-[#D4AF37] shadow-[0_0_20px_rgba(212,175,55,0.15)]': colorMode === 'dark' && isOpen,

            // Light Mode Glass
            '!bg-white/70 !backdrop-blur-2xl border-[#9A7B2F]/20 text-[#1C1B19] hover:border-[#9A7B2F]/50 shadow-md':
              colorMode === 'light' && !disabled,
            '!border-[#8C6D2C] ring-2 ring-[#8C6D2C]/15': colorMode === 'light' && isOpen,
          }
        )}
      >
        <div className='flex items-center gap-3 truncate'>
          {icon && (
            <span
              className={clsx('transition-colors', {
                'text-[#D4AF37]': colorMode === 'dark',
                'text-[#8C6D2C]': colorMode === 'light',
              })}
            >
              {icon}
            </span>
          )}
          <span
            className={clsx('truncate font-medium tracking-wide', {
              'text-white/50': !selectedOption && colorMode === 'dark',
              'text-gray-400': !selectedOption && colorMode === 'light',
            })}
          >
            {selectedOption ? selectedOption.label : t(placeholder)}
          </span>
        </div>

        <RiArrowDownSLine
          className={clsx('w-5 h-5 transition-transform duration-300 flex-shrink-0', {
            'rotate-180': isOpen,
            'text-white/40 group-hover:text-white/80': colorMode === 'dark',
            'text-gray-400 group-hover:text-gray-600': colorMode === 'light',
          })}
        />
      </button>

      {isOpen &&
        createPortal(
          <div
            ref={panelRef}
            role='listbox'
            style={{
              position: 'fixed',
              left: panelPos.left,
              width: panelPos.width,
              top: panelPos.top,
              bottom: panelPos.bottom,
            }}
            className={clsx(
              'premium-dropdown-panel z-[1100] rounded-xl border animate-inc-scale overflow-hidden',
              dropUp ? 'origin-bottom' : 'origin-top',
              {
                'premium-dropdown-panel--dark': colorMode === 'dark',
                'premium-dropdown-panel--light': colorMode === 'light',
              }
            )}
          >
            <div className='max-h-[300px] overflow-y-auto premium-scrollbar p-1.5'>
              {options.map((opt) => {
                const isSelected = value === opt.value;
                return (
                  <button
                    key={opt.value}
                    type='button'
                    onClick={() => {
                      onChange(opt.value);
                      setIsOpen(false);
                    }}
                    className={clsx(
                      'w-full flex items-center justify-between px-3 py-2.5 rounded-lg transition-all duration-200 text-left group',
                      {
                        // Dark Mode variations
                        'bg-white/5 border border-white/5': colorMode === 'dark' && isSelected,
                        'hover:bg-white/5': colorMode === 'dark' && !isSelected,

                        // Light Mode variations
                        'bg-[#8C6D2C]/[0.08] border border-[#8C6D2C]/15': colorMode === 'light' && isSelected,
                        'hover:bg-[#8C6D2C]/[0.05]': colorMode === 'light' && !isSelected,
                      }
                    )}
                  >
                    <div className='flex items-center gap-3 overflow-hidden'>
                      {opt.icon && (
                        <span
                          className={clsx('flex-shrink-0 opacity-70 transition-opacity group-hover:opacity-100', {
                            'text-[#D4AF37]': colorMode === 'dark',
                            'text-[#8C6D2C]': colorMode === 'light',
                          })}
                        >
                          {opt.icon}
                        </span>
                      )}
                      <div className='flex flex-col truncate'>
                        <span
                          className={clsx('text-sm font-medium transition-colors', {
                            'text-white': colorMode === 'dark' && isSelected,
                            'text-white/70 group-hover:text-white': colorMode === 'dark' && !isSelected,

                            'text-[#3B2F14] font-semibold': colorMode === 'light' && isSelected,
                            'text-[#1C1B19]/75 group-hover:text-[#1C1B19]': colorMode === 'light' && !isSelected,
                          })}
                        >
                          {opt.label}
                        </span>
                        {opt.description && (
                          <span
                            className={clsx('text-xs mt-0.5 truncate', {
                              'text-white/40': colorMode === 'dark',
                              'text-[#5C5446]': colorMode === 'light',
                            })}
                          >
                            {opt.description}
                          </span>
                        )}
                      </div>
                    </div>

                    {isSelected && (
                      <RiCheckLine
                        className={clsx('w-5 h-5 flex-shrink-0 ml-3', {
                          'text-[#D4AF37]': colorMode === 'dark',
                          'text-[#8C6D2C]': colorMode === 'light',
                        })}
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>,
          document.body
        )}
    </div>
  );
};
