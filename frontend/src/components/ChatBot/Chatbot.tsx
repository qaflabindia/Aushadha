import React, { FC, lazy, Suspense, useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { TextInput, IconButton, Modal, useCopyToClipboard, SpotlightTarget } from '@neo4j-ndl/react';
import { XMarkIconOutline } from '@neo4j-ndl/react/icons';
import {
  ChatbotProps,
  Chunk,
  Community,
  CustomFile,
  Entity,
  ExtendedNode,
  ExtendedRelationship,
  Messages,
  ResponseMode,
  metricstate,
  multimodelmetric,
  nodeDetailsProps,
} from '../../types';
import { chatBotAPI } from '../../services/QnaAPI';
import { checkTokenLimits } from '../../utils/TokenWarning';
import { showNormalToast } from '../../utils/Toasts';
import { v4 as uuidv4 } from 'uuid';
import { useFileContext } from '../../context/UsersFiles';
import { useCredentials } from '../../context/UserCredentials';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';
import { chatModeLables } from '../../utils/Constants';
import useSpeechSynthesis from '../../hooks/useSpeech';
import FallBackDialog from '../UI/FallBackDialog';
import { getDateTime, shouldShowTokenTracking } from '../../utils/Utils';
import ChatModesSwitch from './ChatModesSwitch';
import CommonActions from './CommonChatActions';
import Loader from '../../utils/Loader';
import remarkGfm from 'remark-gfm';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import { useContext } from 'react';
import useSpeechRecognition from '../../hooks/useSpeechRecognition';
import { useLanguage, useTranslation } from '../../context/LanguageContext';
import { useAlertContext } from '../../context/Alert';
import { RiRobotLine, RiUserLine, RiMicLine, RiMicFill, RiChatSettingsLine } from 'react-icons/ri';
import ChatModeToggle from './ChatModeToggle';

const InfoModal = lazy(() => import('./ChatInfoModal'));
// ... (rest of imports should remain)
if (typeof window !== 'undefined') {
  if (!sessionStorage.getItem('session_id')) {
    const id = uuidv4();
    sessionStorage.setItem('session_id', id);
  }
}
const sessionId = sessionStorage.getItem('session_id') ?? '';
const BACKEND = import.meta.env.VITE_BACKEND_API_URL ?? '';

const Chatbot: FC<ChatbotProps> = (props) => {
  const { colorMode } = useContext(ThemeWrapperContext);
  const t = useTranslation();
  const { messages: listMessages, setMessages: setListMessages, isLoading, isFullScreen, isDeleteChatLoading } = props;
  const [inputMessage, setInputMessage] = useState('');
  const { model, chatModes, selectedRows, filesData, selectedVoice } = useFileContext();
  const { userCredentials } = useCredentials();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [showInfoModal, setShowInfoModal] = useState<boolean>(false);
  const [sourcesModal, setSourcesModal] = useState<string[]>([]);
  const [modelModal, setModelModal] = useState<string>('');
  const [responseTime, setResponseTime] = useState<number>(0);
  const [tokensUsed, setTokensUsed] = useState<number>(0);
  const [cypherQuery, setcypherQuery] = useState<string>('');
  const [chatsMode, setChatsMode] = useState<string>(chatModeLables['graph+vector+fulltext']);
  const [graphEntitites, setgraphEntitites] = useState<[]>([]);
  const [messageError, setmessageError] = useState<string>('');
  const [entitiesModal, setEntitiesModal] = useState<string[]>([]);
  const [nodeDetailsModal, setNodeDetailsModal] = useState<nodeDetailsProps>({});
  const [metricQuestion, setMetricQuestion] = useState<string>('');
  const [metricAnswer, setMetricAnswer] = useState<string>('');
  const [metricContext, setMetricContext] = useState<string>('');
  const [nodes, setNodes] = useState<ExtendedNode[]>([]);
  const [relationships, setRelationships] = useState<ExtendedRelationship[]>([]);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [metricDetails, setMetricDetails] = useState<metricstate | null>(null);
  const [infoEntities, setInfoEntities] = useState<Entity[]>([]);
  const [communities, setCommunities] = useState<Community[]>([]);
  const [infoLoading, toggleInfoLoading] = useReducer((s: boolean) => !s, false);
  const [metricsLoading, toggleMetricsLoading] = useReducer((s: boolean) => !s, false);
  const [activeChat, setActiveChat] = useState<Messages | null>(null);
  const [multiModelMetrics, setMultiModelMetrics] = useState<multimodelmetric[]>([]);
  const [showChatModeOption, setShowChatModeOption] = useState<boolean>(false);
  const chatAnchor = useRef<HTMLButtonElement>(null);

  const { language } = useLanguage();
  const [translationCache, setTranslationCache] = useState<Record<string, string>>({});
  const { transcript, isListening, startListening, stopListening, isSupported, isTranscribing } = useSpeechRecognition({
    language: language.speechCode,
  });
  const [preRecordMessage, setPreRecordMessage] = useState('');

  useEffect(() => {
    if (isListening && transcript) {
      setInputMessage(preRecordMessage ? `${preRecordMessage} ${transcript}` : transcript);
    }
  }, [transcript, isListening, preRecordMessage]);

  const { showAlert } = useAlertContext();

  const handleMicClick = () => {
    if (isListening) {
      stopListening();
    } else {
      setPreRecordMessage(inputMessage);
      startListening();
    }
  };

  const { speak, cancel } = useSpeechSynthesis({
    onEnd: () => {
      setListMessages((msgs) => msgs.map((msg) => ({ ...msg, speaking: false })));
    },
  });

  const [_, copy] = useCopyToClipboard();
  const handleCopy = (message: string, id: number) => {
    copy(message);
    setListMessages((msgs) =>
      msgs.map((msg) => {
        if (msg.id === id) {
          msg.copying = true;
        }
        return msg;
      })
    );
    setTimeout(() => {
      setListMessages((msgs) =>
        msgs.map((msg) => {
          if (msg.id === id) {
            msg.copying = false;
          }
          return msg;
        })
      );
    }, 2000);
  };

  let selectedFileNames: CustomFile[] = filesData.filter(
    (f: CustomFile) => selectedRows.includes(f.id) && ['Completed'].includes(f.status)
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputMessage(e.target.value);
  };

  const saveInfoEntitites = (entities: Entity[]) => {
    setInfoEntities(entities);
  };

  const saveNodes = (chatNodes: ExtendedNode[]) => {
    setNodes(chatNodes);
  };

  const saveChatRelationships = (chatRels: ExtendedRelationship[]) => {
    setRelationships(chatRels);
  };

  const saveChunks = (chatChunks: Chunk[]) => {
    setChunks(chatChunks);
  };
  const saveMultimodemetrics = (metrics: multimodelmetric[]) => {
    setMultiModelMetrics(metrics);
  };
  const saveMetrics = (metricInfo: metricstate) => {
    setMetricDetails(metricInfo);
  };
  const saveCommunities = (chatCommunities: Community[]) => {
    setCommunities(chatCommunities);
  };

  const simulateTypingEffect = (messageId: number, response: ResponseMode, mode: string, message: string) => {
    let index = 0;
    let lastTimestamp: number | null = null;
    const TYPING_INTERVAL = 20;
    const animate = (timestamp: number) => {
      if (lastTimestamp === null) {
        lastTimestamp = timestamp;
      }
      const elapsed = timestamp - lastTimestamp;
      if (elapsed >= TYPING_INTERVAL) {
        if (index < message.length) {
          const nextIndex = index + 1;
          const currentTypedText = message.substring(0, nextIndex);
          setListMessages((msgs) =>
            msgs.map((msg) => {
              if (msg.id === messageId) {
                return {
                  ...msg,
                  modes: { ...msg.modes, [mode]: { ...response, message: currentTypedText } },
                  isTyping: true,
                  speaking: false,
                  copying: false,
                };
              }
              return msg;
            })
          );
          index = nextIndex;
          lastTimestamp = timestamp;
        } else {
          setListMessages((msgs: Messages[]) => {
            const activeMessage = msgs.find((m: Messages) => m.id === messageId);
            let sortedModes: Record<string, ResponseMode> = {};
            if (activeMessage) {
              sortedModes = Object.fromEntries(
                chatModes
                  .filter((m: string) => m in activeMessage.modes)
                  .map((key: string) => [key, activeMessage.modes[key]])
              );
            }
            return msgs.map((msg: Messages) =>
              (msg.id === messageId ? { ...msg, isTyping: false, modes: sortedModes } : msg)
            );
          });
          return;
        }
      }
      requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  };

  const submitQuery = async (query: string) => {
    if (!query.trim()) {
      return;
    }

    if (userCredentials && shouldShowTokenTracking(userCredentials.email)) {
      const tokenCheck = await checkTokenLimits(userCredentials);
      if (tokenCheck.shouldWarn) {
        showNormalToast(tokenCheck.message);
      }
    }

    const datetime = getDateTime();
    const userMsg: Messages = {
      id: Date.now(),
      user: 'user',
      datetime,
      currentMode: chatModes[0],
      modes: { [chatModes[0]]: { message: query } },
    };
    setListMessages([...listMessages, userMsg]);

    const chatbotMsgId = Date.now() + 1;
    const chatbotMsg: Messages = {
      id: chatbotMsgId,
      user: 'chatbot',
      datetime: new Date().toLocaleString(),
      isTyping: true,
      isLoading: true,
      modes: {},
      currentMode: chatModes[0],
    };
    setListMessages((prev) => [...prev, chatbotMsg]);

    abortControllerRef.current = new AbortController();
    const { signal } = abortControllerRef.current;

    try {
      const apiCalls = chatModes.map((mode: string) =>
        chatBotAPI(
          query,
          sessionId,
          model,
          mode,
          selectedFileNames?.map((f) => f.name),
          language.code,
          signal
        )
      );
      const results = await Promise.allSettled(apiCalls);
      results.forEach((result: PromiseSettledResult<any>, index: number) => {
        const mode = chatModes[index];
        if (result.status === 'fulfilled') {
          const res = result.value.response.data;
          if (res.status === 'Success') {
            const responseMode: ResponseMode = {
              message: res.data.message,
              sources: res.data.info.sources,
              model: res.data.info.model,
              total_tokens: res.data.info.total_tokens,
              response_time: res.data.info.response_time,
              cypher_query: res.data.info.cypher_query,
              graphonly_entities: res.data.info.context ?? [],
              entities: res.data.info.entities ?? [],
              nodeDetails: res.data.info.nodedetails,
              error: res.data.info.error,
              metric_question: res.data.info?.metric_details?.question ?? '',
              metric_answer: res.data.info?.metric_details?.answer ?? '',
              metric_contexts: res.data.info?.metric_details?.contexts ?? '',
            };
            if (index === 0) {
              simulateTypingEffect(chatbotMsgId, responseMode, mode, responseMode.message);
            } else {
              setListMessages((prev) =>
                prev.map((msg) =>
                  (msg.id === chatbotMsgId ? { ...msg, modes: { ...msg.modes, [mode]: responseMode } } : msg)
                )
              );
            }
          }
        }
      });
      setListMessages((prev) =>
        prev.map((msg) => (msg.id === chatbotMsgId ? { ...msg, isLoading: false, isTyping: false } : msg))
      );
    } catch (err: any) {
      if (err?.name === 'CanceledError' || err?.message === 'canceled') {
        setListMessages((prev) =>
          prev.map((msg) =>
            (msg.id === chatbotMsgId
              ? {
                  ...msg,
                  isLoading: false,
                  isTyping: false,
                  modes: { ...msg.modes, [chatModes[0]]: { message: 'Generation cancelled by user.' } },
                }
              : msg)
          )
        );
      } else {
        console.error(err);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await submitQuery(inputMessage);
    setInputMessage('');
  };

  useEffect(() => {
    const handleExternalQuery = (event: any) => {
      const { query } = event.detail;
      if (query) {
        submitQuery(query);
      }
    };
    window.addEventListener('external-chat-query', handleExternalQuery);
    return () => window.removeEventListener('external-chat-query', handleExternalQuery);
  }, [listMessages, chatModes, model, userCredentials, language.code]);

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const detailsHandler = useCallback((chat: Messages, previousActiveChat: Messages | null) => {
    const currentMode = chat.modes[chat.currentMode];
    if (!currentMode) {
      return;
    }
    setModelModal(currentMode.model ?? '');
    setSourcesModal(currentMode.sources ?? []);
    setResponseTime(currentMode.response_time ?? 0);
    setTokensUsed(currentMode.total_tokens ?? 0);
    setcypherQuery(currentMode.cypher_query ?? '');
    setShowInfoModal(true);
    setChatsMode(chat.currentMode ?? '');
    setgraphEntitites(currentMode.graphonly_entities ?? []);
    setEntitiesModal(currentMode.entities ?? []);
    setmessageError(currentMode.error ?? '');
    setNodeDetailsModal(currentMode.nodeDetails ?? {});
    setMetricQuestion(currentMode.metric_question ?? '');
    setMetricContext(currentMode.metric_contexts ?? '');
    setMetricAnswer(currentMode.metric_answer ?? '');
    setActiveChat(chat);
    if (
      (previousActiveChat != null && chat.id != previousActiveChat?.id) ||
      (previousActiveChat != null && chat.currentMode != previousActiveChat.currentMode)
    ) {
      setNodes([]);
      setChunks([]);
      setInfoEntities([]);
      setMetricDetails(null);
    }
    if (previousActiveChat != null && chat.id != previousActiveChat?.id) {
      setMultiModelMetrics([]);
    }
  }, []);

  const speechHandler = useCallback(
    async (chat: Messages) => {
      if (chat.speaking) {
        cancel();
        setListMessages((msgs) => msgs.map((msg) => (msg.id === chat.id ? { ...msg, speaking: false } : msg)));
        return;
      }

      const originalText = chat.modes[chat.currentMode]?.message || '';
      const targetLang = language.code;
      let textToSpeak = originalText;

      // 1. Resolve Text (Check Cache or Translate)
      const cacheKey = `${targetLang}:${originalText}`;
      if (translationCache[cacheKey]) {
        textToSpeak = translationCache[cacheKey];
      } else if (targetLang !== 'en' && /^[ \t\r\n!-~]*$/.test(originalText)) {
        try {
          const response = await fetch(`${BACKEND}/audio/translate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              text: originalText,
              target_lang: targetLang,
              source_lang: 'en',
            }),
          });
          if (response.ok) {
            const data = await response.json();
            textToSpeak = data.translatedText;
            setTranslationCache((prev) => ({ ...prev, [cacheKey]: textToSpeak }));
          }
        } catch (error) {
          showAlert('error', 'Translation failed. Please try again.');
        }
      }

      // 2. Play Audio (Browser or Backend Fallback)
      const isBrowserTtsSupported = typeof window !== 'undefined' && window.speechSynthesis !== undefined;
      if (isBrowserTtsSupported) {
        speak({ text: textToSpeak, lang: language.speechCode, voiceURI: selectedVoice }, true);
      } else {
        try {
          const response = await fetch(`${BACKEND}/audio/speak`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: textToSpeak, lang: language.speechCode, voice: selectedVoice }),
          });
          if (response.ok) {
            const audioBlob = await response.blob();
            const url = URL.createObjectURL(audioBlob);
            const audio = new Audio(url);
            audio.onended = () => {
              setListMessages((msgs) => msgs.map((msg) => (msg.id === chat.id ? { ...msg, speaking: false } : msg)));
              URL.revokeObjectURL(url);
            };
            audio.play();
          }
        } catch (error) {
          showAlert('error', 'Speech synthesis failed. Please try again.');
        }
      }

      setListMessages((msgs) => {
        const messageWithSpeaking = msgs.find((msg) => msg.speaking);
        return msgs.map((msg) => (msg.id === chat.id && !messageWithSpeaking ? { ...msg, speaking: true } : msg));
      });
    },
    [speak, cancel, language, translationCache]
  );

  const handleSwitchMode = (messageId: number, newMode: string) => {
    setListMessages((prev) => prev.map((msg) => (msg.id === messageId ? { ...msg, currentMode: newMode } : msg)));
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [listMessages]);

  return (
    <div
      className={clsx(
        'flex! flex-col justify-between min-h-full max-h-full overflow-hidden relative transition-all duration-700 glass-luxe',
        {
          'bg-[#080808]/40': colorMode === 'dark',
          'bg-white/40': colorMode === 'light',
        }
      )}
    >
      {/* Sticky Chat Header */}
      <div
        className={clsx('sticky top-0 z-20 px-8 py-5 border-b backdrop-blur-3xl flex items-center justify-between', {
          'bg-black/60 border-white/5 shadow-2xl': colorMode === 'dark',
          'bg-white/60 border-gray-100': colorMode === 'light',
        })}
      >
        <div className='flex flex-col'>
          <span
            className={clsx('text-[10px] uppercase tracking-[0.3em] font-extrabold', {
              'text-[#D4AF37]': colorMode === 'dark',
              'text-[#1A1A1A]': colorMode === 'light',
            })}
          >
            {t('conciergeIntelligence')}
          </span>
          <span
            className={clsx('text-[8px] uppercase tracking-[0.2em] font-bold mt-1 opacity-40', {
              'text-[#D4AF37]': colorMode === 'dark',
              'text-gray-500': colorMode === 'light',
            })}
          >
            {t('neuralNetwork')}
          </span>
        </div>
        <div
          className={clsx('w-2 h-2 rounded-full animate-pulse', {
            'bg-[#D4AF37] shadow-[0_0_8px_#D4AF37]': colorMode === 'dark',
            'bg-blue-500 shadow-[0_0_8px_#3B82F6]': colorMode === 'light',
          })}
        />
      </div>
      {isDeleteChatLoading && (
        <div className='absolute inset-0 z-50 bg-black/60 backdrop-blur-xl flex items-center justify-center'>
          <Loader title='Processing Architecture...' />
        </div>
      )}

      {/* Signature Message Stream */}
      <div className='flex-grow overflow-y-auto overflow-x-hidden p-6 pt-28 gap-8 flex flex-col custom-scrollbar'>
        {listMessages.length > 0 &&
          listMessages.map((chat, index) => {
            const messagechatModes = Object.keys(chat.modes);
            return (
              <div
                key={chat.id + index}
                className={clsx('flex flex-col gap-3 w-full animate-fade-in-up', {
                  'items-start': chat.user === 'chatbot',
                  'items-end': chat.user !== 'chatbot',
                })}
              >
                {/* Precision Persona Badge */}
                <div className='flex items-center gap-3 px-2'>
                  {chat.user === 'chatbot' ? (
                    <>
                      <div className='w-7 h-7 rounded-full border border-[#D4AF37]/30 flex items-center justify-center bg-[#D4AF37]/5 shadow-[0_0_15px_rgba(212,175,55,0.1)]'>
                        <RiRobotLine className='text-[#D4AF37] w-3.5 h-3.5' />
                      </div>
                      <span
                        className={clsx('text-[9px] tracking-concierge font-extrabold uppercase', {
                          'text-[#D4AF37]/60': colorMode === 'dark',
                          'text-[#D4AF37]': colorMode === 'light',
                        })}
                      >
                        {t('conciergeIntelligence')}
                      </span>
                    </>
                  ) : (
                    <>
                      <span
                        className={clsx('text-[9px] tracking-concierge font-extrabold uppercase', {
                          'text-white/30': colorMode === 'dark',
                          'text-black/40': colorMode === 'light',
                        })}
                      >
                        {t('authorizedTerminal')}
                      </span>
                      <div
                        className={clsx('w-7 h-7 rounded-full border flex items-center justify-center', {
                          'border-white/10 bg-white/5': colorMode === 'dark',
                          'border-gray-200 bg-gray-50': colorMode === 'light',
                        })}
                      >
                        <RiUserLine
                          className={clsx('w-3.5 h-3.5', {
                            'text-white/40': colorMode === 'dark',
                            'text-black/40': colorMode === 'light',
                          })}
                        />
                      </div>
                    </>
                  )}
                </div>

                {/* Glass Concierge Card */}
                <div
                  className={clsx(
                    `p-6 rounded-[24px] border-grad-gs glass-luxe transition-all duration-700`,
                    {
                      'shadow-2xl': chat.user === 'chatbot',
                      'bg-[#D4AF37]/5': chat.user !== 'chatbot' && colorMode === 'dark',
                      'bg-blue-50/50': chat.user !== 'chatbot' && colorMode === 'light',
                    },
                    isFullScreen ? 'max-w-[75%]' : 'max-w-[95%]'
                  )}
                >
                  <div
                    className={clsx(
                      'prose prose-sm max-w-none [&_*]:!text-inherit [&_a]:!text-[#D4AF37] [&_code]:!text-[#D4AF37]',
                      {
                        'prose-invert': colorMode === 'dark',
                      }
                    )}
                  >
                    <div
                      className={clsx('leading-relaxed font-normal antialiased', {
                        'text-white/95': chat.user === 'chatbot' && colorMode === 'dark',
                        'text-[#D4AF37] font-semibold': chat.user !== 'chatbot' && colorMode === 'dark',
                        'text-[#1A1A1A]': chat.user === 'chatbot' && colorMode === 'light',
                        'text-blue-700 font-semibold': chat.user !== 'chatbot' && colorMode === 'light',
                      })}
                      style={{
                        color:
                          chat.user === 'chatbot' && colorMode === 'dark'
                            ? 'rgba(255,255,255,0.95)'
                            : chat.user !== 'chatbot' && colorMode === 'dark'
                              ? '#D4AF37'
                              : '#1A1A1A',
                      }}
                    >
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {chat.id === 2 && chat.user === 'chatbot' && index === 0
                          ? t('welcomeMessage')
                          : chat.modes[chat.currentMode]?.message || ''}
                      </ReactMarkdown>
                    </div>
                  </div>

                  {chat.user === 'chatbot' && !chat.isLoading && !chat.isTyping && (
                    <div className='mt-5 flex items-center justify-between border-t border-white/5 pt-4'>
                      <CommonActions
                        chat={chat}
                        copyHandler={handleCopy}
                        detailsHandler={detailsHandler}
                        listMessages={listMessages}
                        speechHandler={speechHandler}
                        activeChat={activeChat}
                      />
                      {messagechatModes.length > 1 && (
                        <ChatModesSwitch
                          currentMode={chat.currentMode}
                          switchToOtherMode={(idx: number) => handleSwitchMode(chat.id, messagechatModes[idx])}
                          isFullScreen={isFullScreen ?? false}
                          currentModeIndex={messagechatModes.indexOf(chat.currentMode)}
                          modescount={messagechatModes.length}
                        />
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        <div ref={messagesEndRef} />
      </div>

      {/* Precision Signature Input Area */}
      <div
        className={clsx('p-8 border-t transition-all duration-500 glass-luxe', {
          'border-white/5 shadow-[0_-20px_50px_rgba(0,0,0,0.5)]': colorMode === 'dark',
          'border-gray-100': colorMode === 'light',
        })}
      >
        <form onSubmit={handleSubmit} className='flex gap-4 items-center w-full'>
          <div className='flex-1 relative group w-full'>
            <TextInput
              isDisabled={isLoading}
              value={inputMessage}
              onChange={handleInputChange}
              isFluid
              placeholder={t('inquireVault')}
              className={clsx('focus:border-[#D4AF37]/50 py-4 px-12 rounded-2xl w-full', {
                'text-white shadow-inner': colorMode === 'dark',
                'text-black': colorMode === 'light',
              })}
              aria-label='chatbot-input'
            />
            <button
              type='button'
              ref={chatAnchor}
              onClick={() => setShowChatModeOption(true)}
              className={clsx(
                'absolute left-4 top-1/2 -translate-y-1/2 p-2 rounded-full transition-all duration-300 hover:bg-[#D4AF37]/10',
                {
                  'text-[#D4AF37]': colorMode === 'dark',
                  'text-gray-500': colorMode === 'light',
                }
              )}
              title='Intelligence Search Mode'
            >
              <RiChatSettingsLine size={18} />
            </button>

            {isSupported && (
              <button
                type='button'
                onClick={handleMicClick}
                disabled={isTranscribing}
                className={clsx(
                  'absolute right-4 top-1/2 -translate-y-1/2 p-2 rounded-full transition-all duration-300',
                  {
                    'text-[#D4AF37] scale-110 shadow-[0_0_15px_#D4AF37] bg-[#D4AF37]/10': isListening,
                    'text-white/40 hover:text-white/60': !isListening && colorMode === 'dark',
                    'text-gray-400 hover:text-gray-600': !isListening && colorMode === 'light',
                    'opacity-50 cursor-not-allowed': isTranscribing,
                  }
                )}
              >
                {isListening ? (
                  <RiMicFill size={20} className='animate-pulse' />
                ) : isTranscribing ? (
                  <div className='w-5 h-5 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin' />
                ) : (
                  <RiMicLine size={20} />
                )}
              </button>
            )}
          </div>
          <SpotlightTarget id='chatbtn' hasPulse={true} indicatorVariant='border'>
            {isLoading ? (
              <button
                type='button'
                onClick={handleCancel}
                className={clsx(
                  'h-[54px] px-8 rounded-2xl flex items-center justify-center transition-all duration-500 translate-y-[-1px]',
                  {
                    'bg-red-900/40 text-red-500 font-extrabold uppercase tracking-[0.15em] text-[10px] border border-red-500/30 hover:bg-red-900/60':
                      colorMode === 'dark',
                    'bg-red-100 text-red-600 font-bold uppercase tracking-widest text-[10px] hover:bg-red-200':
                      colorMode === 'light',
                  }
                )}
              >
                Cancel
              </button>
            ) : (
              <button
                type='submit'
                disabled={isLoading || !inputMessage.trim()}
                className={clsx(
                  'h-[54px] px-10 rounded-2xl flex items-center justify-center transition-all duration-500 disabled:opacity-20 translate-y-[-1px]',
                  {
                    'bg-gradient-to-br from-[#D4AF37] to-[#E5E4E2] text-black font-extrabold uppercase tracking-[0.2em] text-[10px] shadow-[0_4px_25px_rgba(212,175,55,0.3)] hover:shadow-[0_8px_35px_rgba(212,175,55,0.5)]':
                      colorMode === 'dark',
                    'bg-blue-600 text-white font-bold uppercase tracking-widest text-[10px]': colorMode === 'light',
                  }
                )}
              >
                Ask
              </button>
            )}
          </SpotlightTarget>
        </form>
      </div>

      <Suspense fallback={<FallBackDialog />}>
        <Modal
          modalProps={{ id: 'retrieval-info' }}
          onClose={() => setShowInfoModal(false)}
          isOpen={showInfoModal}
          size={'large'}
        >
          <div className='flex justify-end p-4'>
            <IconButton size='large' isClean ariaLabel='close' onClick={() => setShowInfoModal(false)}>
              <XMarkIconOutline className='w-6 h-6' />
            </IconButton>
          </div>
          <InfoModal
            sources={sourcesModal}
            model={modelModal}
            entities_ids={entitiesModal}
            response_time={responseTime}
            total_tokens={tokensUsed}
            mode={chatsMode}
            cypher_query={cypherQuery}
            graphonly_entities={graphEntitites}
            error={messageError}
            nodeDetails={nodeDetailsModal}
            metricanswer={metricAnswer}
            metriccontexts={metricContext}
            metricquestion={metricQuestion}
            metricmodel={model}
            nodes={nodes}
            infoEntities={infoEntities}
            relationships={relationships}
            chunks={chunks}
            metricDetails={activeChat != undefined && metricDetails != null ? metricDetails : undefined}
            communities={communities}
            infoLoading={infoLoading}
            metricsLoading={metricsLoading}
            saveInfoEntitites={saveInfoEntitites}
            saveChatRelationships={saveChatRelationships}
            saveChunks={saveChunks}
            saveCommunities={saveCommunities}
            saveMetrics={saveMetrics}
            saveNodes={saveNodes}
            toggleInfoLoading={toggleInfoLoading}
            toggleMetricsLoading={toggleMetricsLoading}
            saveMultimodemetrics={saveMultimodemetrics}
            activeChatmodes={activeChat?.modes}
            multiModelMetrics={multiModelMetrics}
            metricError={metricDetails?.error ?? ''}
          />
        </Modal>
      </Suspense>
      <ChatModeToggle
        closeHandler={(_, reason) => {
          if (reason.type === 'backdropClick' || reason.type === 'itemClick') {
            setShowChatModeOption(false);
          }
        }}
        open={showChatModeOption}
        menuAnchor={chatAnchor}
        isRoot={false}
      />
    </div>
  );
};

export default Chatbot;
