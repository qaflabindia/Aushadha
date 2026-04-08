import React, { useState, useContext, useRef } from 'react';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import clsx from 'clsx';
import { useTranslation } from '../../hooks/useTranslation';
import {
  RiUserSettingsLine,
  RiGlobalLine,
  RiShieldUserLine,
  RiRobotLine,
  RiDatabase2Line,
  RiSunLine,
  RiMoonLine,
  RiLogoutBoxLine,
  RiArrowDownSLine,
  RiVipDiamondLine,
} from 'react-icons/ri';
import { useGoogleAuth } from '../../context/GoogleAuthContext';
import { Avatar, Banner } from '@neo4j-ndl/react';
import LanguageSelector from '../UI/LanguageSelector';
import PatientDropdown from '../User/PatientDropdown';
import { OptionType } from '../../types';
import GraphSettingsTabs from './GraphSettingsTabs';
import AdminPage from '../Admin/AdminPage';
import { useFileContext } from '../../context/UsersFiles';
import { usePatientContext } from '../../context/PatientContext';
import { llms } from '../../utils/Constants';
import { capitalizeWithUnderscore } from '../../utils/Utils';
import ChatModeToggle from '../ChatBot/ChatModeToggle';
import { getSecrets, saveSecret } from '../../services/SecretAPI';
import { TextInput, Button } from '@neo4j-ndl/react';
import { LockClosedIconOutline } from '@neo4j-ndl/react/icons';

type TabKey = 'general' | 'ai' | 'account' | 'admin' | 'graph' | 'security';

// ─── Section Components ────────────────────────────────────────────────────────

const SectionHeader: React.FC<{ title: string; subtitle?: string }> = ({ title, subtitle }) => {
  const { colorMode } = useContext(ThemeWrapperContext);
  return (
    <div className='mb-8'>
      <h2
        className={clsx('text-2xl font-bold', {
          'text-white': colorMode === 'dark',
          'text-gray-900': colorMode === 'light',
        })}
      >
        {title}
      </h2>
      {subtitle && (
        <p
          className={clsx('text-sm mt-1', {
            'text-white/50': colorMode === 'dark',
            'text-gray-500': colorMode === 'light',
          })}
        >
          {subtitle}
        </p>
      )}
      <div
        className={clsx('mt-4 h-px', {
          'bg-white/10': colorMode === 'dark',
          'bg-gray-200': colorMode === 'light',
        })}
      />
    </div>
  );
};

const SettingRow: React.FC<{ label: string; description?: string; children: React.ReactNode }> = ({
  label,
  description,
  children,
}) => {
  const { colorMode } = useContext(ThemeWrapperContext);
  return (
    <div
      className={clsx('flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-5 border-b', {
        'border-white/5': colorMode === 'dark',
        'border-gray-100': colorMode === 'light',
      })}
    >
      <div className='flex-1'>
        <p
          className={clsx('text-sm font-semibold', {
            'text-white/80': colorMode === 'dark',
            'text-gray-700': colorMode === 'light',
          })}
        >
          {label}
        </p>
        {description && (
          <p
            className={clsx('text-xs mt-0.5', {
              'text-white/40': colorMode === 'dark',
              'text-gray-400': colorMode === 'light',
            })}
          >
            {description}
          </p>
        )}
      </div>
      <div className='flex-shrink-0'>{children}</div>
    </div>
  );
};

// ─── General Settings ────────────────────────────────────────────────────────
const GeneralSettings: React.FC = () => {
  const t = useTranslation();
  const { colorMode, toggleColorMode } = useContext(ThemeWrapperContext);
  return (
    <div>
      <SectionHeader
        title={t('General Workstation')}
        subtitle={t('Display, language and workspace appearance preferences.')}
      />
      <SettingRow label={t('Interface Language')} description={t('Select your preferred language for the UI.')}>
        <LanguageSelector />
      </SettingRow>
      <SettingRow label={t('Theme')} description={t('Toggle between Dark (Luxury) and Light mode.')}>
        <button
          onClick={toggleColorMode}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-semibold transition-all duration-300',
            {
              'border-white/10 text-white/70 hover:text-white hover:border-white/30 bg-white/5': colorMode === 'dark',
              'border-gray-200 text-gray-600 hover:text-gray-900 hover:border-gray-300 bg-gray-50':
                colorMode === 'light',
            }
          )}
        >
          {colorMode === 'dark' ? (
            <>
              <RiSunLine className='w-4 h-4' /> {t('Switch to Light')}
            </>
          ) : (
            <>
              <RiMoonLine className='w-4 h-4' /> {t('Switch to Dark')}
            </>
          )}
        </button>
      </SettingRow>
    </div>
  );
};

const AccountSettings: React.FC = () => {
  const t = useTranslation();
  const { colorMode } = useContext(ThemeWrapperContext);
  const { user, logout, isAuthenticated } = useGoogleAuth();
  const [passwords, setPasswords] = useState({ new: '', confirm: '' });
  const [passStatus, setPassStatus] = useState<{ type: 'success' | 'danger'; message: string } | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const { getAuthHeaders } = useGoogleAuth();
  const apiBase = import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000';

  const handleUpdatePassword = async () => {
    if (!passwords.new || !passwords.confirm) {
      setPassStatus({ type: 'danger', message: t('All fields are required') });
      return;
    }
    if (passwords.new !== passwords.confirm) {
      setPassStatus({ type: 'danger', message: t('Passwords do not match') });
      return;
    }
    if (passwords.new.length < 6) {
      setPassStatus({ type: 'danger', message: t('Password must be at least 6 characters') });
      return;
    }

    setIsUpdating(true);
    setPassStatus(null);
    try {
      const resp = await fetch(`${apiBase}/update-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({ password: passwords.new }),
      });
      const data = await resp.json();
      if (data.status === 'Success') {
        setPassStatus({ type: 'success', message: t('Password updated successfully') });
        setPasswords({ new: '', confirm: '' });
      } else {
        setPassStatus({ type: 'danger', message: data.message || data.error || t('Update failed') });
      }
    } catch {
      setPassStatus({ type: 'danger', message: t('Network error') });
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div>
      <SectionHeader
        title={t('Account & Context')}
        subtitle={t('Your profile, active patient context, and session management.')}
      />
      {isAuthenticated && user && (
        <div
          className={clsx('flex items-center gap-5 p-5 rounded-2xl mb-6 border', {
            'bg-white/5 border-white/10': colorMode === 'dark',
            'bg-gray-50 border-gray-200': colorMode === 'light',
          })}
        >
          <Avatar name={user.name ?? user.email} source={user.picture ?? undefined} />
          <div>
            <p
              className={clsx('font-bold text-base', {
                'text-white': colorMode === 'dark',
                'text-gray-900': colorMode === 'light',
              })}
            >
              {user.name ?? 'User'}
            </p>
            <p
              className={clsx('text-xs mt-0.5', {
                'text-white/50': colorMode === 'dark',
                'text-gray-500': colorMode === 'light',
              })}
            >
              {user.email}
            </p>
            <span
              className={clsx(
                'inline-block mt-1 text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border',
                {
                  'border-[#D4AF37]/40 text-[#D4AF37] bg-[#D4AF37]/10': colorMode === 'dark',
                  'border-blue-200 text-blue-600 bg-blue-50': colorMode === 'light',
                }
              )}
            >
              {user.role ?? 'User'}
            </span>
          </div>
        </div>
      )}

      {user?.role?.toUpperCase() !== 'PATIENT' && (
        <SettingRow
          label={t('Active Patient Context')}
          description={t('Select the patient to personalise the clinical AI context.')}
        >
          <PatientDropdown />
        </SettingRow>
      )}

      {/* Password Management */}
      <div
        className={clsx('mt-8 p-6 rounded-2xl border', {
          'bg-white/5 border-white/10': colorMode === 'dark',
          'bg-gray-50 border-gray-200': colorMode === 'light',
        })}
      >
        <p
          className={clsx('text-sm font-bold mb-4', {
            'text-white': colorMode === 'dark',
            'text-gray-900': colorMode === 'light',
          })}
        >
          {t('Change Password')}
        </p>
        <div className='space-y-4'>
          <TextInput
            placeholder={t('New Password')}
            htmlAttributes={{ type: 'password' }}
            value={passwords.new}
            onChange={(e) => setPasswords((p) => ({ ...p, new: e.target.value }))}
            isFluid
          />
          <TextInput
            placeholder={t('Confirm New Password')}
            htmlAttributes={{ type: 'password' }}
            value={passwords.confirm}
            onChange={(e) => setPasswords((p) => ({ ...p, confirm: e.target.value }))}
            isFluid
          />
          {passStatus && (
            <Banner type={passStatus.type} isCloseable onClose={() => setPassStatus(null)}>
              {passStatus.message}
            </Banner>
          )}
          <Button onClick={handleUpdatePassword} isLoading={isUpdating} className='w-full'>
            {t('Update Password')}
          </Button>
        </div>
      </div>

      <div className='mt-8'>
        <SettingRow label={t('Session')} description={t('Log out of the application.')}>
          <button
            onClick={() => {
              logout();
              window.location.href = '/login';
            }}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-semibold transition-all duration-300',
              {
                'border-red-500/40 text-red-400 hover:text-red-300 hover:border-red-400/60 bg-red-500/10':
                  colorMode === 'dark',
                'border-red-200 text-red-600 hover:border-red-400 bg-red-50': colorMode === 'light',
              }
            )}
          >
            <RiLogoutBoxLine className='w-4 h-4' />
            {t('Logout')}
          </button>
        </SettingRow>
      </div>
    </div>
  );
};

// ─── AI Engine & Sources ────────────────────────────────────────────────────────
const AISettings: React.FC = () => {
  const t = useTranslation();
  const { colorMode } = useContext(ThemeWrapperContext);
  const { model, setModel, setFilesData, selectedVoice, setSelectedVoice } = useFileContext();
  const { selectedPatient } = usePatientContext();
  const patientEmail = selectedPatient?.case_id || 'global';
  const [isOpen, setIsOpen] = useState(false);
  const chatAnchor = useRef<HTMLDivElement>(null);
  const [showChatModeToggle, setShowChatModeToggle] = useState(false);

  const handleModelChange = (selectedValue: string) => {
    setModel(selectedValue);
    localStorage.setItem(`${patientEmail}_selectedModel`, selectedValue);
    setFilesData((prevfiles) =>
      prevfiles.map((curfile) => ({
        ...curfile,
        model:
          curfile.status === 'New' || curfile.status === 'Ready to Reprocess' || curfile.status === 'Failed'
            ? selectedValue
            : curfile.model,
      }))
    );
    setIsOpen(false);
  };

  return (
    <div>
      <SectionHeader
        title={t('AI Engine & Sources')}
        subtitle={t('Configure the LLM model and chatbot retrieval settings.')}
      />

      {/* LLM Selection */}
      <SettingRow
        label={t('LLM Model')}
        description={t('Select the language model for knowledge extraction and chat.')}
      >
        <div className='relative' style={{ minWidth: 200 }}>
          <button
            onClick={() => setIsOpen(!isOpen)}
            className={clsx(
              'w-full flex items-center justify-between gap-3 px-4 py-2 rounded-lg border text-sm font-semibold transition-all',
              {
                '!bg-black/70 !backdrop-blur-2xl border-white/20 text-white hover:border-[#D4AF37]/50 hover:shadow-[0_0_20px_rgba(212,175,55,0.1)]':
                  colorMode === 'dark',
                '!bg-white/70 !backdrop-blur-2xl border-gray-200 text-gray-700 hover:border-blue-400 shadow-md':
                  colorMode === 'light',
                'border-[#D4AF37] shadow-[0_0_20px_rgba(212,175,55,0.15)]': colorMode === 'dark' && isOpen,
                'border-blue-500 ring-2 ring-blue-500/20': colorMode === 'light' && isOpen,
              }
            )}
          >
            <span>{model ? capitalizeWithUnderscore(model) : t('Select Model')}</span>
            <RiArrowDownSLine className={clsx('w-4 h-4 transition-transform', { 'rotate-180': isOpen })} />
          </button>

          {isOpen && (
            <div
              className={clsx(
                'absolute top-full left-0 mt-1 w-full rounded-xl border shadow-2xl z-[1100] overflow-auto',
                {
                  '!bg-black/70 !backdrop-blur-2xl border-white/20 max-h-72': colorMode === 'dark',
                  '!bg-white/70 !backdrop-blur-2xl border-gray-200 shadow-2xl max-h-72': colorMode === 'light',
                }
              )}
            >
              {llms.map((llmOption) => (
                <button
                  key={llmOption}
                  onClick={() => handleModelChange(llmOption)}
                  className={clsx('w-full text-left px-4 py-2.5 text-xs transition-all', {
                    'hover:bg-white/5 text-white/80': colorMode === 'dark',
                    'hover:bg-gray-50 text-gray-700': colorMode === 'light',
                    'bg-white/10 font-bold': colorMode === 'dark' && model === llmOption,
                    'bg-blue-50 font-bold text-blue-700': colorMode === 'light' && model === llmOption,
                  })}
                >
                  {capitalizeWithUnderscore(llmOption)}
                </button>
              ))}
            </div>
          )}
        </div>
      </SettingRow>

      {/* Chat Source / Mode */}
      <SettingRow
        label={t('Chat Retrieval Mode')}
        description={t('Configure which knowledge sources the AI assistant uses during chat.')}
      >
        <div ref={chatAnchor}>
          <button
            onClick={() => setShowChatModeToggle(true)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-semibold transition-all',
              {
                'border-white/10 text-white/70 hover:text-white hover:border-white/30 bg-white/5': colorMode === 'dark',
                'border-gray-200 text-gray-600 hover:text-gray-900 bg-gray-50': colorMode === 'light',
              }
            )}
          >
            {t('Configure Sources')}
          </button>
          <ChatModeToggle
            open={showChatModeToggle}
            menuAnchor={chatAnchor}
            isRoot={false}
            closeHandler={(_, reason) => {
              if (reason.type === 'backdropClick' || reason.type === 'escapeKeyDown' || reason.type === 'itemClick') {
                setShowChatModeToggle(false);
              }
            }}
          />
        </div>
      </SettingRow>

      {/* Assistant Voice */}
      <SettingRow label={t('Assistant Voice')} description={t('Select the voice for text-to-speech responses.')}>
        <div className='flex gap-2 flex-wrap'>
          {['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'].map((v) => (
            <button
              key={v}
              onClick={() => {
                setSelectedVoice(v);
                localStorage.setItem(`${patientEmail}_selectedVoice`, v);
              }}
              className={clsx('px-3 py-1 rounded-full border text-xs font-bold transition-all', {
                'bg-[#D4AF37] text-black border-[#D4AF37]': selectedVoice === v && colorMode === 'dark',
                'bg-blue-600 text-white border-blue-600': selectedVoice === v && colorMode === 'light',
                'border-white/10 text-white/40 hover:text-white/70': selectedVoice !== v && colorMode === 'dark',
                'border-gray-200 text-gray-500 hover:text-gray-800': selectedVoice !== v && colorMode === 'light',
              })}
            >
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
      </SettingRow>
    </div>
  );
};

// ─── Graph Settings (placeholder for full dialog) ──────────────────────────────
// ─── Graph Settings ──────────────────────────────────────────────────────────
const GraphSettingsSection: React.FC<{
  combinedPatterns: string[];
  setCombinedPatterns: React.Dispatch<React.SetStateAction<string[]>>;
  combinedNodes: OptionType[];
  setCombinedNodes: React.Dispatch<React.SetStateAction<OptionType[]>>;
  combinedRels: OptionType[];
  setCombinedRels: React.Dispatch<React.SetStateAction<OptionType[]>>;
}> = ({ combinedPatterns, setCombinedPatterns, combinedNodes, setCombinedNodes, combinedRels, setCombinedRels }) => {
  const t = useTranslation();
  return (
    <div>
      <SectionHeader title={t('Graph Settings')} subtitle={t('Knowledge graph construction and schema settings.')} />
      <div className='mt-6'>
        <GraphSettingsTabs
          combinedPatterns={combinedPatterns}
          setCombinedPatterns={setCombinedPatterns}
          combinedNodes={combinedNodes}
          setCombinedNodes={setCombinedNodes}
          combinedRels={combinedRels}
          setCombinedRels={setCombinedRels}
        />
      </div>
    </div>
  );
};

// ─── Administration & Security ─────────────────────────────────────────────────
const SecuritySection: React.FC = () => {
  const t = useTranslation();
  const { colorMode } = useContext(ThemeWrapperContext);
  const [secretName, setSecretName] = useState('');
  const [secretValue, setSecretValue] = useState('');
  const [status, setStatus] = useState<{ type: 'success' | 'danger'; message: string } | null>(null);
  const [existingSecrets, setExistingSecrets] = useState<string[]>([]);
  const [secretsLoaded, setSecretsLoaded] = useState(false);

  const fetchSecrets = async () => {
    try {
      const response = await getSecrets();
      if (response.data.status === 'Success') {
        setExistingSecrets(response.data.data);
        setSecretsLoaded(true);
      }
    } catch {
      /* silence */
    }
  };

  const handleSave = async () => {
    if (!secretName || !secretValue) {
      setStatus({ type: 'danger', message: 'Both name and value are required.' });
      return;
    }
    try {
      const response = await saveSecret(secretName, secretValue);
      if (response.data.status === 'Success') {
        setStatus({ type: 'success', message: response.data.message });
        setSecretName('');
        setSecretValue('');
        fetchSecrets();
      } else {
        setStatus({ type: 'danger', message: response.data.error || 'Failed to save secret.' });
      }
    } catch {
      setStatus({ type: 'danger', message: 'Network error.' });
    }
  };

  return (
    <div>
      <SectionHeader
        title={t('Secure Vault')}
        subtitle={t('Store API keys and secrets securely. Used as backend environment overrides.')}
      />

      {status && (
        <div className='mb-4'>
          <Banner type={status.type} isCloseable onClose={() => setStatus(null)}>
            {status.message}
          </Banner>
        </div>
      )}

      <div className='space-y-4 mb-6'>
        <div>
          <label
            className={clsx('block text-xs font-semibold mb-1 uppercase tracking-wider', {
              'text-white/60': colorMode === 'dark',
              'text-gray-500': colorMode === 'light',
            })}
          >
            {t('Secret Name')}
          </label>
          <TextInput
            value={secretName}
            onChange={(e) => setSecretName(e.target.value)}
            placeholder='e.g. OPENAI_API_KEY'
            isFluid
          />
        </div>
        <div>
          <label
            className={clsx('block text-xs font-semibold mb-1 uppercase tracking-wider', {
              'text-white/60': colorMode === 'dark',
              'text-gray-500': colorMode === 'light',
            })}
          >
            {t('Secret Value')}
          </label>
          <TextInput
            htmlAttributes={{ type: 'password' }}
            value={secretValue}
            onChange={(e) => setSecretValue(e.target.value)}
            placeholder='••••••••••••••••'
            isFluid
          />
        </div>
        <Button onClick={handleSave}>{t('Save Secret')}</Button>
      </div>

      <div
        className={clsx('pt-4 border-t', {
          'border-white/10': colorMode === 'dark',
          'border-gray-200': colorMode === 'light',
        })}
      >
        <div className='flex items-center justify-between mb-3'>
          <p
            className={clsx('text-xs font-bold uppercase tracking-widest', {
              'text-[#D4AF37]': colorMode === 'dark',
              'text-blue-600': colorMode === 'light',
            })}
          >
            {t('Configured Secrets')}
          </p>
          {!secretsLoaded && (
            <button
              onClick={fetchSecrets}
              className={clsx('text-xs hover:underline', {
                'text-white/40': colorMode === 'dark',
                'text-gray-400': colorMode === 'light',
              })}
            >
              {t('Load')}
            </button>
          )}
        </div>
        <div className='flex flex-wrap gap-2'>
          {existingSecrets.length > 0 ? (
            existingSecrets.map((key) => (
              <div
                key={key}
                className={clsx(
                  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border',
                  {
                    'border-[#D4AF37]/30 text-[#D4AF37] bg-[#D4AF37]/10': colorMode === 'dark',
                    'border-blue-200 text-blue-600 bg-blue-50': colorMode === 'light',
                  }
                )}
              >
                <LockClosedIconOutline className='w-3 h-3' />
                {key}
              </div>
            ))
          ) : (
            <p
              className={clsx('text-xs italic', {
                'text-white/30': colorMode === 'dark',
                'text-gray-400': colorMode === 'light',
              })}
            >
              {t('No secrets configured yet. Click Load to check.')}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

// ─── Administration ────────────────────────────────────────────────────────────
const AdminSection: React.FC = () => {
  const t = useTranslation();
  const { user } = useGoogleAuth();
  const { colorMode } = useContext(ThemeWrapperContext);

  if (user?.role?.toUpperCase() !== 'ADMIN') {
    return (
      <div>
        <SectionHeader title={t('Administration')} />
        <div
          className={clsx('flex flex-col items-center justify-center gap-3 py-20 rounded-2xl border border-dashed', {
            'border-white/10 text-white/30': colorMode === 'dark',
            'border-gray-200 text-gray-400': colorMode === 'light',
          })}
        >
          <RiShieldUserLine className='w-10 h-10 opacity-40' />
          <p className='text-sm'>{t('Administrator access required.')}</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <SectionHeader title={t('Administration')} subtitle={t('Manage users, roles, and organisation settings.')} />
      <div
        className='rounded-2xl overflow-hidden border'
        style={{ border: '1px solid rgba(255,255,255,0.05)', minHeight: 400 }}
      >
        <AdminPage embedded />
      </div>
    </div>
  );
};

// ─── Main SettingsPage ─────────────────────────────────────────────────────────
interface SettingsPageProps {
  combinedPatterns: string[];
  setCombinedPatterns: React.Dispatch<React.SetStateAction<string[]>>;
  combinedNodes: OptionType[];
  setCombinedNodes: React.Dispatch<React.SetStateAction<OptionType[]>>;
  combinedRels: OptionType[];
  setCombinedRels: React.Dispatch<React.SetStateAction<OptionType[]>>;
}

const SettingsPage: React.FC<SettingsPageProps> = ({
  combinedPatterns,
  setCombinedPatterns,
  combinedNodes,
  setCombinedNodes,
  combinedRels,
  setCombinedRels,
}) => {
  const { colorMode } = useContext(ThemeWrapperContext);
  const t = useTranslation();
  const { user } = useGoogleAuth();
  const [activeTab, setActiveTab] = useState<TabKey>('general');
  const isPatient = user?.role?.toUpperCase() === 'PATIENT';

  const tabs: { id: TabKey; label: string; icon: React.ReactNode }[] = (
    [
      { id: 'general', label: t('General'), icon: <RiGlobalLine className='w-5 h-5' /> },
      { id: 'account', label: t('Account & Context'), icon: <RiUserSettingsLine className='w-5 h-5' /> },
      { id: 'ai', label: t('AI Engine & Sources'), icon: <RiRobotLine className='w-5 h-5' /> },
      { id: 'graph', label: t('Graph Settings'), icon: <RiDatabase2Line className='w-5 h-5' /> },
      { id: 'security', label: t('Secure Vault'), icon: <RiVipDiamondLine className='w-5 h-5' /> },
      { id: 'admin', label: t('Administration'), icon: <RiShieldUserLine className='w-5 h-5' /> },
    ] as { id: TabKey; label: string; icon: React.ReactNode }[]
  ).filter((tab) => {
    if (isPatient) {
      return tab.id === 'account' || tab.id === 'general';
    }
    return true;
  });

  return (
    <div className={clsx("flex h-full w-full font-['Inter'] overflow-hidden")}>
      {/* Sidebar */}
      <aside
        className={clsx('w-64 flex-shrink-0 flex flex-col py-8', {
          'border-r border-white/5': colorMode === 'dark',
          'border-r border-gray-100 bg-gray-50/60': colorMode === 'light',
        })}
      >
        <div className='px-6 mb-8'>
          <h1
            className={clsx('text-lg font-black tracking-tight', {
              'text-white': colorMode === 'dark',
              'text-gray-900': colorMode === 'light',
            })}
          >
            {t('Settings')}
          </h1>
          <p
            className={clsx('text-[10px] mt-0.5 font-bold uppercase tracking-[0.2em] opacity-60', {
              'text-[#D4AF37]': colorMode === 'dark',
              'text-blue-600': colorMode === 'light',
            })}
          >
            {t('Workspace Control Center')}
          </p>
        </div>

        <nav className='flex-1 overflow-y-auto px-3 space-y-1'>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200',
                {
                  'bg-white/10 text-white shadow-inner': colorMode === 'dark' && activeTab === tab.id,
                  'text-white/50 hover:text-white hover:bg-white/5': colorMode === 'dark' && activeTab !== tab.id,
                  'bg-blue-600 text-white shadow-sm': colorMode === 'light' && activeTab === tab.id,
                  'text-gray-500 hover:text-gray-900 hover:bg-gray-100': colorMode === 'light' && activeTab !== tab.id,
                }
              )}
            >
              <span
                className={clsx({
                  'text-[#D4AF37]': colorMode === 'dark' && activeTab === tab.id,
                  'text-white': colorMode === 'light' && activeTab === tab.id,
                })}
              >
                {tab.icon}
              </span>
              {tab.label}
            </button>
          ))}
        </nav>
      </aside>

      {/* Content */}
      <main
        className={clsx('flex-1 overflow-y-auto p-8 lg:p-12', {
          'bg-black/10': colorMode === 'dark',
          'bg-white': colorMode === 'light',
        })}
      >
        <div className='max-w-2xl mx-auto'>
          {activeTab === 'general' && <GeneralSettings />}
          {activeTab === 'account' && <AccountSettings />}
          {activeTab === 'ai' && <AISettings />}
          {activeTab === 'graph' && (
            <GraphSettingsSection
              combinedPatterns={combinedPatterns}
              setCombinedPatterns={setCombinedPatterns}
              combinedNodes={combinedNodes}
              setCombinedNodes={setCombinedNodes}
              combinedRels={combinedRels}
              setCombinedRels={setCombinedRels}
            />
          )}
          {activeTab === 'security' && <SecuritySection />}
          {activeTab === 'admin' && <AdminSection />}
        </div>
      </main>
    </div>
  );
};

export default SettingsPage;
