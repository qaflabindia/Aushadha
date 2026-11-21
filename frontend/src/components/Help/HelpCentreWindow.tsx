import React, { useCallback, useContext, useEffect, useRef, useState } from 'react';
import clsx from 'clsx';
import { RiQuestionLine, RiSubtractLine, RiCloseLine, RiRefreshLine } from 'react-icons/ri';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import { useGoogleAuth } from '../../context/GoogleAuthContext';
import { url } from '../../utils/Utils';
import { useTranslation } from '../../hooks/useTranslation';
import { OPEN_HELP_EVENT } from './helpLinks';
import HelpFeedback, { shouldAskFeedback } from './HelpFeedback';

// Help Centre: a floating window that shows the help document (backend/help/help-centre.html,
// served by GET /help/document to signed-in users only). It can be dragged, resized and
// minimised, and stays open while the user moves around the app.
//
// The document runs in a sandboxed frame without same-origin access, so it cannot read the
// login token. It talks to this window by postMessage:
//   document -> window: {type:'ready'} | {type:'save', id, text} | {type:'reset', id}
//   window -> document: {type:'init', theme, isAdmin, role, topic} | {type:'theme', theme}
//                       {type:'goto', id}   (open a topic; see helpLinks.tsx)
//   document -> window: {type:'contact', href}  (mailto link; opened by the app)
//                       {type:'saved', id, data} | {type:'error', id, message}
// Saving goes through POST /help/edit and /help/reset, which only admins may call.

type WindowState = { open: boolean; minimized: boolean; x: number; y: number; w: number; h: number };

const STORAGE_KEY = 'aushadha.help.window';
const MIN_W = 360;
const MIN_H = 320;

const defaultState = (): WindowState => {
  const w = Math.min(560, window.innerWidth - 32);
  const h = Math.min(720, window.innerHeight - 96);
  return { open: false, minimized: false, x: window.innerWidth - w - 24, y: 72, w, h };
};

const clamp = (s: WindowState): WindowState => {
  const w = Math.max(MIN_W, Math.min(s.w, window.innerWidth - 16));
  const h = Math.max(MIN_H, Math.min(s.h, window.innerHeight - 16));
  const x = Math.max(8, Math.min(s.x, window.innerWidth - w - 8));
  const y = Math.max(8, Math.min(s.y, window.innerHeight - 48));
  return { ...s, w, h, x, y };
};

const loadState = (): WindowState => {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    if (saved && typeof saved.x === 'number') {
      return clamp({ ...defaultState(), ...saved });
    }
  } catch {
    // storage blocked or corrupt: use the defaults
  }
  return defaultState();
};

const HelpCentreWindow: React.FC = () => {
  const { colorMode } = useContext(ThemeWrapperContext);
  const { user } = useGoogleAuth();
  const t = useTranslation();
  const isAdmin = (user?.role || '').toUpperCase() === 'ADMIN';
  const role = isAdmin ? 'admin' : (user?.role || '').toUpperCase() === 'PATIENT' ? 'patient' : 'staff';
  const dark = colorMode !== 'light';

  const [state, setState] = useState<WindowState>(loadState);
  const [doc, setDoc] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [interacting, setInteracting] = useState(false);
  const [askingFeedback, setAskingFeedback] = useState(false);
  const frameRef = useRef<HTMLIFrameElement>(null);
  // Topic to open once the document is ready (deep link before the window was open)
  const pendingTopic = useRef<string | undefined>(undefined);
  const frameReady = useRef(false);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // storage blocked: the window just won't remember its place
    }
  }, [state]);

  useEffect(() => {
    const onResize = () => setState((s) => clamp(s));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const loadDocument = useCallback(async () => {
    setLoadError(null);
    try {
      const res = await fetch(`${url()}/help/document`, { cache: 'no-store' });
      if (!res.ok) {
        throw new Error(res.status === 401 ? 'Sign in again to open the Help Centre.' : `Error ${res.status}`);
      }
      const html = await res.text();
      // Images in the document use paths like /help/x.png, served by this app
      const base = `<base href="${window.location.origin}/">`;
      frameReady.current = false;
      setDoc(html.replace(/<head>/i, `<head>${base}`));
    } catch (e: any) {
      setLoadError(e?.message || 'Could not load the Help Centre.');
    }
  }, []);

  useEffect(() => {
    if (state.open && doc === null) {
      loadDocument();
    }
  }, [state.open, doc, loadDocument]);

  const post = useCallback((message: object) => {
    frameRef.current?.contentWindow?.postMessage(message, '*');
  }, []);

  useEffect(() => {
    post({ type: 'theme', theme: dark ? 'dark' : 'light' });
  }, [dark, post]);

  useEffect(() => {
    const onMessage = async (event: MessageEvent) => {
      // Only listen to our own frame
      if (!frameRef.current || event.source !== frameRef.current.contentWindow) {
        return;
      }
      const msg = event.data || {};
      if (msg.type === 'ready') {
        frameReady.current = true;
        post({ type: 'init', theme: dark ? 'dark' : 'light', isAdmin, role, topic: pendingTopic.current });
        pendingTopic.current = undefined;
        return;
      }
      if ((msg.type === 'save' || msg.type === 'reset') && typeof msg.id === 'string') {
        try {
          const res = await fetch(`${url()}/help/${msg.type === 'save' ? 'edit' : 'reset'}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(
              msg.type === 'save' ? { section_id: msg.id, text: String(msg.text ?? '') } : { section_id: msg.id }
            ),
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            throw new Error(data?.detail || `Error ${res.status}`);
          }
          post({ type: 'saved', id: msg.id, data });
        } catch (e: any) {
          post({ type: 'error', id: msg.id, message: e?.message || 'Could not save' });
        }
        return;
      }
      // Mail links: the sandboxed frame can't open them itself
      if (msg.type === 'contact' && typeof msg.href === 'string' && /^mailto:[^\s<>"']+$/.test(msg.href)) {
        window.location.href = msg.href;
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [dark, isAdmin, role, post]);

  // Deep links: openHelp('topic') opens the window at that topic
  useEffect(() => {
    const onOpen = (e: Event) => {
      const topic = (e as CustomEvent<{ topic?: string }>).detail?.topic;
      setState((s) => clamp({ ...s, open: true, minimized: false }));
      if (topic && frameReady.current) {
        post({ type: 'goto', id: topic });
      } else {
        pendingTopic.current = topic;
      }
    };
    window.addEventListener(OPEN_HELP_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_HELP_EVENT, onOpen);
  }, [post]);

  const closeWindow = () => {
    frameReady.current = false;
    setAskingFeedback(false);
    // Load it fresh next time, so new edits and feedback show
    setDoc(null);
    setState((s) => ({ ...s, open: false, minimized: false }));
  };

  // Drag by the title bar, resize by the corner handle
  const startPointer = (mode: 'move' | 'resize') => (e: React.PointerEvent) => {
    if (e.button !== 0) {
      return;
    }
    e.preventDefault();
    const start = { px: e.clientX, py: e.clientY, ...state };
    setInteracting(true);
    const onMove = (ev: PointerEvent) => {
      const dx = ev.clientX - start.px;
      const dy = ev.clientY - start.py;
      setState((s) =>
        clamp(mode === 'move' ? { ...s, x: start.x + dx, y: start.y + dy } : { ...s, w: start.w + dx, h: start.h + dy })
      );
    };
    const onUp = () => {
      setInteracting(false);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };

  const surface = dark
    ? 'bg-[#0d0d10]/95 border border-[#D4AF37]/25 text-white'
    : 'bg-white/95 border border-[#9A7B2F]/20 text-gray-900';
  const iconButton = clsx(
    'w-7 h-7 inline-flex items-center justify-center rounded-lg transition-colors',
    dark ? 'text-white/60 hover:text-[#D4AF37] hover:bg-white/5' : 'text-gray-500 hover:text-[#9A7B2F] hover:bg-black/5'
  );

  // Minimised keeps the document mounted (hidden), so the reader keeps their place
  const launcher = (
    <button
      type='button'
      onClick={() => setState((s) => clamp({ ...s, open: true, minimized: false }))}
      aria-label={t('Open Help Centre')}
      title={t('Help Centre')}
      className={clsx(
        'fixed bottom-5 right-5 z-[1100] inline-flex items-center gap-2 rounded-full shadow-2xl backdrop-blur-xl transition-all',
        surface,
        state.minimized ? 'px-4 h-11 text-sm font-semibold' : 'w-11 h-11 justify-center',
        dark ? 'hover:border-[#D4AF37]/60' : 'hover:border-[#9A7B2F]/50'
      )}
    >
      <RiQuestionLine className={clsx('w-5 h-5', dark ? 'text-[#D4AF37]' : 'text-[#9A7B2F]')} />
      {state.minimized && <span>{t('Help Centre')}</span>}
    </button>
  );

  return (
    <>
      {(!state.open || state.minimized) && launcher}
      {state.open && (
        <div
          role='dialog'
          aria-label={t('Help Centre')}
          className={clsx(
            'fixed z-[1200] flex flex-col rounded-2xl shadow-2xl backdrop-blur-xl overflow-hidden',
            surface,
            state.minimized && 'hidden'
          )}
          style={{ left: state.x, top: state.y, width: state.w, height: state.h }}
        >
          <div
            onPointerDown={startPointer('move')}
            className={clsx(
              'flex items-center justify-between gap-2 px-4 h-11 shrink-0 cursor-move select-none',
              dark ? 'border-b border-[#D4AF37]/15' : 'border-b border-[#9A7B2F]/15'
            )}
          >
            <div className='flex items-center gap-2 min-w-0'>
              <RiQuestionLine className={clsx('w-5 h-5 shrink-0', dark ? 'text-[#D4AF37]' : 'text-[#9A7B2F]')} />
              <span className='text-sm font-bold tracking-tight truncate'>{t('Help Centre')}</span>
            </div>
            <div className='flex items-center gap-1' onPointerDown={(e) => e.stopPropagation()}>
              <button
                type='button'
                className={iconButton}
                onClick={() => {
                  frameReady.current = false;
                  setDoc(null);
                }}
                aria-label={t('Reload')}
                title={t('Reload')}
              >
                <RiRefreshLine className='w-4 h-4' />
              </button>
              <button
                type='button'
                className={iconButton}
                onClick={() => setState((s) => ({ ...s, minimized: true }))}
                aria-label={t('Minimise')}
                title={t('Minimise')}
              >
                <RiSubtractLine className='w-4 h-4' />
              </button>
              <button
                type='button'
                className={iconButton}
                onClick={() => {
                  // Ask "was it helpful?" once per session before closing
                  if (shouldAskFeedback() && doc !== null) {
                    setAskingFeedback(true);
                    return;
                  }
                  closeWindow();
                }}
                aria-label={t('Close')}
                title={t('Close')}
              >
                <RiCloseLine className='w-4 h-4' />
              </button>
            </div>
          </div>

          <div className='relative flex-1 min-h-0'>
            {askingFeedback && <HelpFeedback dark={dark} onDone={closeWindow} />}
            {loadError ? (
              <div className='h-full flex flex-col items-center justify-center gap-3 p-6 text-center text-sm opacity-80'>
                <p>{loadError}</p>
                <button
                  type='button'
                  className={clsx(iconButton, 'w-auto px-3')}
                  onClick={() => {
                    frameReady.current = false;
                    setDoc(null);
                  }}
                >
                  {t('Try again')}
                </button>
              </div>
            ) : doc === null ? (
              <div className='h-full flex items-center justify-center text-sm opacity-60'>{t('Loading…')}</div>
            ) : (
              <iframe
                ref={frameRef}
                title={t('Help Centre')}
                srcDoc={doc}
                sandbox='allow-scripts'
                className='w-full h-full border-0 bg-transparent'
              />
            )}
            {/* Keeps the frame from swallowing the pointer while dragging or resizing */}
            {interacting && <div className='absolute inset-0' />}
          </div>

          <div
            onPointerDown={startPointer('resize')}
            className='absolute right-0 bottom-0 w-4 h-4 cursor-nwse-resize'
            aria-hidden='true'
            style={{
              background: `linear-gradient(135deg, transparent 55%, ${dark ? 'rgba(212,175,55,0.5)' : 'rgba(154,123,47,0.45)'} 55%)`,
            }}
          />
        </div>
      )}
    </>
  );
};

export default HelpCentreWindow;
