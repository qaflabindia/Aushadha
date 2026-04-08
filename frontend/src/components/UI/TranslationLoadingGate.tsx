import React from 'react';
import { useTranslation2 } from '../../context/TranslationContext';
import clsx from 'clsx';

export const TranslationLoadingGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isLoading } = useTranslation2();

  return (
    <>
      <div
        className={clsx(
          'fixed inset-0 z-[9999] flex flex-col items-center justify-center transition-opacity duration-700 pointer-events-none',
          {
            'opacity-100': isLoading,
            'opacity-0': !isLoading,
          }
        )}
      >
        <div className='flex flex-col items-center gap-4'>
          <div className='w-12 h-12 border-4 border-[#D4AF37]/30 border-t-[#D4AF37] rounded-full animate-spin'></div>
          <span className='font-medium text-sm tracking-widest uppercase text-white/80'>Translating Interface</span>
        </div>
      </div>
      <div className='opacity-100 transition-opacity duration-700'>{children}</div>
    </>
  );
};
