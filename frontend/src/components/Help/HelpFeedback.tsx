import React, { useState } from 'react';
import clsx from 'clsx';
import { RiThumbUpLine, RiThumbDownLine } from 'react-icons/ri';
import { url } from '../../utils/Utils';
import { useTranslation } from '../../hooks/useTranslation';

// "Was the Help Centre helpful?" shown when the Help Centre window is closed, once per
// browser session. Answers go to POST /help/feedback; admins read them in the Help Centre
// under Audit & feedback.

const ASKED_KEY = 'aushadha.help.feedbackAsked';

export const shouldAskFeedback = (): boolean => {
  try {
    return sessionStorage.getItem(ASKED_KEY) === null;
  } catch {
    return false; // storage blocked: don't nag on every close
  }
};

const markAsked = () => {
  try {
    sessionStorage.setItem(ASKED_KEY, '1');
  } catch {
    // nothing to remember
  }
};

const HelpFeedback: React.FC<{ dark: boolean; onDone: () => void }> = ({ dark, onDone }) => {
  const t = useTranslation();
  const [helpful, setHelpful] = useState<boolean | null>(null);
  const [comment, setComment] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const finish = () => {
    markAsked();
    onDone();
  };

  const send = async () => {
    if (helpful === null) {
      return;
    }
    setSending(true);
    setError(null);
    try {
      const res = await fetch(`${url()}/help/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ helpful, comment: comment.trim() }),
      });
      if (!res.ok) {
        throw new Error(`Error ${res.status}`);
      }
      finish();
    } catch {
      setSending(false);
      setError(t('Could not send your feedback. Try again, or skip.'));
    }
  };

  const choice = (value: boolean, label: string, Icon: typeof RiThumbUpLine) => (
    <button
      type='button'
      onClick={() => setHelpful(value)}
      aria-pressed={helpful === value}
      className={clsx(
        'flex-1 flex flex-col items-center gap-2 py-4 rounded-xl border transition-colors',
        helpful === value
          ? dark
            ? 'border-[#D4AF37] bg-[#D4AF37]/10 text-white'
            : 'border-[#9A7B2F] bg-[#9A7B2F]/10 text-gray-900'
          : dark
            ? 'border-white/10 text-white/70 hover:border-[#D4AF37]/50'
            : 'border-black/10 text-gray-600 hover:border-[#9A7B2F]/50'
      )}
    >
      <Icon className={clsx('w-6 h-6', dark ? 'text-[#D4AF37]' : 'text-[#9A7B2F]')} />
      <span className='text-sm font-semibold'>{label}</span>
    </button>
  );

  return (
    <div
      className={clsx(
        'absolute inset-0 z-10 flex items-center justify-center p-6 backdrop-blur-md',
        dark ? 'bg-black/70' : 'bg-white/80'
      )}
    >
      <div className='w-full max-w-sm'>
        <p
          className={clsx(
            'text-[10px] font-bold uppercase tracking-[0.2em]',
            dark ? 'text-[#D4AF37]' : 'text-[#9A7B2F]'
          )}
        >
          {t('Before you go')}
        </p>
        <h3 className='text-lg font-bold mt-1 mb-4'>{t('Was the Help Centre helpful?')}</h3>
        <div className='flex gap-3'>
          {choice(true, t('Yes'), RiThumbUpLine)}
          {choice(false, t('No'), RiThumbDownLine)}
        </div>
        {helpful !== null && (
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value.slice(0, 1000))}
            rows={3}
            placeholder={
              helpful ? t('Anything we could make even better? (optional)') : t('What were you looking for? (optional)')
            }
            className={clsx(
              'mt-4 w-full rounded-xl p-3 text-sm outline-none resize-none border',
              dark
                ? 'bg-white/5 border-white/10 text-white placeholder:text-white/30 focus:border-[#D4AF37]/60'
                : 'bg-white border-black/10 text-gray-900 placeholder:text-gray-400 focus:border-[#9A7B2F]/60'
            )}
          />
        )}
        {error && <p className='mt-2 text-xs text-red-400'>{error}</p>}
        <div className='flex items-center justify-end gap-2 mt-4'>
          <button
            type='button'
            onClick={finish}
            className={clsx(
              'px-3 py-2 rounded-lg text-sm',
              dark ? 'text-white/50 hover:text-white' : 'text-gray-500 hover:text-gray-900'
            )}
          >
            {t('Skip')}
          </button>
          <button
            type='button'
            onClick={send}
            disabled={helpful === null || sending}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-semibold transition-opacity disabled:opacity-40',
              dark ? 'bg-[#D4AF37] text-black' : 'bg-[#9A7B2F] text-white'
            )}
          >
            {sending ? t('Sending…') : t('Send feedback')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default HelpFeedback;
