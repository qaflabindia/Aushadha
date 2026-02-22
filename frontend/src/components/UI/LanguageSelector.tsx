import React, { useState, useRef, useEffect } from 'react';
import { useContext } from 'react';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import { useLanguage, SUPPORTED_LANGUAGES } from '../../context/LanguageContext';
import clsx from 'clsx';
import { RiGlobalLine } from 'react-icons/ri';

const LanguageSelector: React.FC = () => {
  const { colorMode } = useContext(ThemeWrapperContext);
  const { language, setLanguageByCode } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

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
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          "flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all duration-300 text-[10px] uppercase tracking-widest font-bold group",
          {
            'border-white/10 hover:border-[#D4AF37]/30 hover:shadow-[0_0_15px_rgba(212,175,55,0.1)]': colorMode === 'dark',
            'border-gray-200 hover:border-blue-300': colorMode === 'light',
          }
        )}
        title="Select Language"
      >
        <RiGlobalLine className={clsx("w-4 h-4 transition-colors", {
          'text-[#D4AF37] group-hover:text-[#D4AF37]': colorMode === 'dark',
          'text-gray-500 group-hover:text-blue-500': colorMode === 'light',
        })} />
        <span className={clsx("transition-colors", {
          'text-white/60 group-hover:text-white': colorMode === 'dark',
          'text-gray-600 group-hover:text-gray-800': colorMode === 'light',
        })}>
          {language.name}
        </span>
      </button>

      {isOpen && (
        <div className={clsx(
          "absolute top-full right-0 mt-2 min-w-[200px] py-2 rounded-2xl border z-[100] backdrop-blur-3xl shadow-2xl animate-fade-in-up",
          {
            'bg-[#0a0a0a]/95 border-white/10': colorMode === 'dark',
            'bg-white/95 border-gray-200': colorMode === 'light',
          }
        )}>
          <div className={clsx("px-4 py-2 text-[8px] uppercase tracking-[0.3em] font-bold border-b mb-1", {
            'text-[#D4AF37]/40 border-white/5': colorMode === 'dark',
            'text-gray-400 border-gray-100': colorMode === 'light',
          })}>
            Select Language
          </div>
          {SUPPORTED_LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => {
                setLanguageByCode(lang.code);
                setIsOpen(false);
              }}
              className={clsx(
                "w-full px-4 py-2.5 flex items-center justify-between text-left transition-all duration-200",
                {
                  'hover:bg-[#D4AF37]/10': colorMode === 'dark',
                  'hover:bg-blue-50': colorMode === 'light',
                },
                language.code === lang.code && {
                  'bg-[#D4AF37]/5 border-l-2 border-[#D4AF37]': colorMode === 'dark',
                  'bg-blue-50 border-l-2 border-blue-500': colorMode === 'light',
                }
              )}
            >
              <div className="flex items-center gap-3">
                <span className={clsx("text-sm font-medium", {
                  'text-white/90': colorMode === 'dark',
                  'text-gray-800': colorMode === 'light',
                })}>{lang.name}</span>
                <span className={clsx("text-[10px] opacity-40", {
                  'text-white': colorMode === 'dark',
                  'text-gray-500': colorMode === 'light',
                })}>{lang.nameEn}</span>
              </div>
              {language.code === lang.code && (
                <div className={clsx("w-1.5 h-1.5 rounded-full", {
                  'bg-[#D4AF37] shadow-[0_0_8px_#D4AF37]': colorMode === 'dark',
                  'bg-blue-500': colorMode === 'light',
                })} />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default LanguageSelector;
