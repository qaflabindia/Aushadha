import React, { useState, useRef, useEffect, useContext } from 'react';
import clsx from 'clsx';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import { RiArrowDownSLine, RiCheckLine } from 'react-icons/ri';

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
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find((opt) => opt.value === value);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
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
            'bg-black/40 border-white/10 text-white hover:border-[#D4AF37]/50 hover:shadow-[0_0_20px_rgba(212,175,55,0.1)]':
              colorMode === 'dark' && !disabled,
            'border-[#D4AF37] shadow-[0_0_20px_rgba(212,175,55,0.15)]': colorMode === 'dark' && isOpen,

            // Light Mode Glass
            'bg-white/80 border-gray-200 text-gray-900 hover:border-blue-400 hover:shadow-sm backdrop-blur-md':
              colorMode === 'light' && !disabled,
            'border-blue-500 ring-2 ring-blue-500/20': colorMode === 'light' && isOpen,
          }
        )}
      >
        <div className='flex items-center gap-3 truncate'>
          {icon && (
            <span
              className={clsx('transition-colors', {
                'text-[#D4AF37]': colorMode === 'dark',
                'text-blue-600': colorMode === 'light',
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
            {selectedOption ? selectedOption.label : placeholder}
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

      {isOpen && (
        <div
          className={clsx(
            'absolute z-[1100] w-full mt-2 rounded-xl border shadow-[0_20px_50px_rgba(0,0,0,0.5)] origin-top animate-inc-scale overflow-hidden',
            {
              '!bg-[#0F1014] border-white/10': colorMode === 'dark',
              '!bg-white border-gray-100 shadow-xl': colorMode === 'light',
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
                      'bg-blue-50/80 border border-blue-100': colorMode === 'light' && isSelected,
                      'hover:bg-gray-50': colorMode === 'light' && !isSelected,
                    }
                  )}
                >
                  <div className='flex items-center gap-3 overflow-hidden'>
                    {opt.icon && (
                      <span
                        className={clsx('flex-shrink-0 opacity-70 transition-opacity group-hover:opacity-100', {
                          'text-[#D4AF37]': colorMode === 'dark',
                          'text-blue-600': colorMode === 'light',
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

                          'text-blue-900': colorMode === 'light' && isSelected,
                          'text-gray-700 group-hover:text-gray-900': colorMode === 'light' && !isSelected,
                        })}
                      >
                        {opt.label}
                      </span>
                      {opt.description && (
                        <span
                          className={clsx('text-xs mt-0.5 truncate', {
                            'text-white/40': colorMode === 'dark',
                            'text-gray-500': colorMode === 'light',
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
                        'text-blue-600': colorMode === 'light',
                      })}
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
