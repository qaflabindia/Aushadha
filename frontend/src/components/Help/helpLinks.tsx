import React from 'react';
import clsx from 'clsx';
import { RiQuestionLine } from 'react-icons/ri';

// Deep links into the Help Centre. Call openHelp('settings-vault') from anywhere in the app,
// or place a <HelpLink topic='settings-vault' />. The topic is a section id (e.g.
// 'administration') or '<section id>-<topic id>' as listed in backend/help/content.json.

export const OPEN_HELP_EVENT = 'aushadha:open-help';

export const openHelp = (topic?: string) => {
  window.dispatchEvent(new CustomEvent(OPEN_HELP_EVENT, { detail: { topic } }));
};

export const HelpLink: React.FC<{ topic: string; label: string; dark: boolean; className?: string }> = ({
  topic,
  label,
  dark,
  className,
}) => (
  <button
    type='button'
    onClick={() => openHelp(topic)}
    title={label}
    aria-label={label}
    className={clsx(
      'inline-flex items-center justify-center w-7 h-7 rounded-lg transition-colors shrink-0',
      dark
        ? 'text-white/40 hover:text-[#D4AF37] hover:bg-white/5'
        : 'text-gray-400 hover:text-[#9A7B2F] hover:bg-black/5',
      className
    )}
  >
    <RiQuestionLine className='w-4 h-4' />
  </button>
);
