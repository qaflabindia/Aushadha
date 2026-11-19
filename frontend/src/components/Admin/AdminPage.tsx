import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Typography,
  DataGrid,
  DataGridComponents,
  Flex,
  LoadingSpinner,
  Banner,
  Button,
  TextInput,
} from '@neo4j-ndl/react';
import { useReactTable, getCoreRowModel, createColumnHelper } from '@tanstack/react-table';
import { useGoogleAuth } from '../../context/GoogleAuthContext';
import { useTranslation } from '../../hooks/useTranslation';
import axios from 'axios';
import { PremiumDropdown } from '../UI/PremiumDropdown';
import { RiLockLine, RiDeleteBinLine } from 'react-icons/ri';
import { SUPPORTED_LANGUAGES } from '../../context/LangTypes';

interface UserRecord {
  id: number;
  email: string;
  role: string;
  case_id: string | null;
  created_at: string;
}

interface TranslationStat {
  lang: string;
  total: number;
  translated: number;
  coverage: number;
}

const AdminPage: React.FC<{ embedded?: boolean }> = ({ embedded: _embedded = false }) => {
  const { getAuthHeaders, user: currentUser } = useGoogleAuth();
  const t = useTranslation();
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [alert, setAlert] = useState<{ type: 'success' | 'danger'; message: string } | null>(null);

  const [isAddingUser, setIsAddingUser] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserRole, setNewUserRole] = useState('Patient');
  const [newUserCaseId, setNewUserCaseId] = useState('');

  const [transStats, setTransStats] = useState<TranslationStat[]>([]);
  const [seedLanguage, setSeedLanguage] = useState('hi');
  const [isSeedingTranslations, setIsSeedingTranslations] = useState(false);

  const apiBase = import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000';
  const columnHelper = createColumnHelper<UserRecord>();

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const headers = getAuthHeaders();
      const [usersRes, rolesRes, statsRes] = await Promise.all([
        axios.get(`${apiBase}/rbac/users`, { headers }),
        axios.get(`${apiBase}/rbac/roles`, { headers }),
        axios.get(`${apiBase}/translate/ui/stats`, { headers }),
      ]);
      setUsers(usersRes.data || []);
      setRoles(rolesRes.data || []);
      const byLang = statsRes.data.by_language || {};
      const totalKeys = statsRes.data.total_keys || 0;
      const stats = Object.entries(byLang).map(([lang, s]: [string, any]) => ({
        lang,
        total: totalKeys,
        translated: s.translated || 0,
        coverage: totalKeys > 0 ? (s.translated / totalKeys) * 100 : 0,
      }));
      setTransStats(stats);
    } catch (err) {
      console.error('Failed to fetch admin data', err);
      // Ensure we don't crash if stats aren't available
      setAlert({ type: 'danger', message: t('Failed to load some management data. Check backend logs.') as any });
    } finally {
      setIsLoading(false);
    }
  }, [apiBase, getAuthHeaders, t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateUser = async () => {
    if (!newUserEmail || !newUserEmail.includes('@')) {
      setAlert({ type: 'danger', message: t('Please enter a valid email address.') });
      return;
    }

    setIsAddingUser(true);
    try {
      const headers = getAuthHeaders();
      const payload: { email: string; role_name: string; case_id?: string } = {
        email: newUserEmail.toLowerCase(),
        role_name: newUserRole,
      };
      if (newUserRole === 'Patient' && newUserCaseId.trim()) {
        payload.case_id = newUserCaseId.trim();
      }

      await axios.post(`${apiBase}/rbac/assign_role`, payload, { headers });
      const caseNote = newUserRole === 'Patient' ? ` (Case ID: ${newUserCaseId.trim() || 'auto-generated'})` : '';
      setAlert({
        type: 'success',
        message: `${t('Successfully registered')} ${newUserEmail} ${t('as')} ${newUserRole}${caseNote}`,
      });
      setNewUserEmail('');
      setNewUserCaseId('');
      fetchData();
    } catch (err: any) {
      console.error('Failed to create user', err);
      const detail = err?.response?.data?.detail || `${t('Failed to create user')} ${newUserEmail}`;
      setAlert({ type: 'danger', message: detail });
    } finally {
      setIsAddingUser(false);
    }
  };

  const handleRoleChange = useCallback(
    async (email: string, newRole: string, existingCaseId: string | null) => {
      // If user already has a case_id and admin is re-assigning Patient role, inform them it's locked
      if (newRole === 'Patient' && existingCaseId) {
        setAlert({
          type: 'danger',
          message: `Case ID '${existingCaseId}' is already assigned to ${email} and cannot be changed.`,
        });
        return;
      }
      try {
        const headers = getAuthHeaders();
        await axios.post(`${apiBase}/rbac/assign_role`, { email, role_name: newRole }, { headers });
        setAlert({ type: 'success', message: `${t('Successfully assigned')} ${newRole} ${t('to')} ${email}` });
        fetchData();
      } catch (err: any) {
        console.error('Failed to assign role', err);
        const detail = err?.response?.data?.detail || `${t('Failed to assign role to')} ${email}`;
        setAlert({ type: 'danger', message: detail });
      }
    },
    [apiBase, getAuthHeaders, fetchData, t]
  );

  const handleDeleteUser = async (user: UserRecord) => {
    if (
      !window.confirm(
        `Are you sure you want to delete user ${user.email}? All associated data and patient assignments will be removed.`
      )
    ) {
      return;
    }
    try {
      const headers = getAuthHeaders();
      await axios.delete(`${apiBase}/rbac/user/${user.id}`, { headers });
      setAlert({ type: 'success', message: `Successfully deleted user ${user.email}` });
      fetchData();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || `Failed to delete user ${user.email}`;
      setAlert({ type: 'danger', message: detail });
    }
  };

  const handleSeedTranslations = async () => {
    setIsSeedingTranslations(true);
    try {
      const headers = getAuthHeaders();
      const response = await axios.post(`${apiBase}/translate/ui/seed?lang=${encodeURIComponent(seedLanguage)}`, null, {
        headers,
        timeout: 300000,
      });

      const seeded = response?.data?.seeded ?? 0;
      setAlert({
        type: 'success',
        message:
          seeded > 0
            ? `${t('Translation seeding completed for')} ${seedLanguage.toUpperCase()}: ${seeded} ${t('entries added')}.`
            : `${t('No new translation entries were needed for')} ${seedLanguage.toUpperCase()}.`,
      });
      await fetchData();
    } catch (err: any) {
      console.error('Failed to seed translations', err);
      const detail =
        err?.response?.data?.error ||
        err?.response?.data?.message ||
        `${t('Translation seeding failed for')} ${seedLanguage.toUpperCase()}.`;
      setAlert({ type: 'danger', message: detail });
    } finally {
      setIsSeedingTranslations(false);
    }
  };

  const columns = useMemo(
    () => [
      columnHelper.accessor('email', {
        header: t('Email'),
        cell: (info) => <Typography variant='body-medium'>{info.getValue()}</Typography>,
      }),
      columnHelper.accessor('role', {
        header: t('Current Role'),
        cell: (info) => {
          const { email } = info.row.original;
          const currentRole = info.getValue();
          const existingCaseId = info.row.original.case_id;

          return (
            <div style={{ width: '220px' }}>
              <PremiumDropdown
                value={currentRole || 'None'}
                options={roles.map((r) => ({ label: r, value: r }))}
                onChange={(newValue: string) => handleRoleChange(email, newValue, existingCaseId)}
                disabled={email === currentUser?.email}
              />
            </div>
          );
        },
      }),
      columnHelper.accessor('case_id', {
        header: t('Case ID'),
        cell: (info) => {
          const caseId = info.getValue();
          const { role } = info.row.original;
          if (role !== 'Patient' || !caseId) {
            return (
              <Typography variant='body-small' className='opacity-40'>
                —
              </Typography>
            );
          }
          return (
            <div className='flex items-center gap-2'>
              <Typography variant='body-small' className='font-mono font-bold'>
                {caseId}
              </Typography>
              <RiLockLine size={12} className='opacity-40' title='Case ID is immutable' />
            </div>
          );
        },
      }),
      columnHelper.accessor('created_at', {
        header: t('Joined'),
        cell: (info) => <Typography variant='body-small'>{new Date(info.getValue()).toLocaleDateString()}</Typography>,
      }),
      columnHelper.display({
        id: 'actions',
        header: t('Actions'),
        cell: (info) => (
          <Button
            size='small'
            onClick={() => handleDeleteUser(info.row.original)}
            isDisabled={info.row.original.email === currentUser?.email}
            style={{ background: 'transparent', border: 'none' }}
          >
            <RiDeleteBinLine className='text-red-500' size={18} />
          </Button>
        ),
      }),
    ],
    [roles, currentUser, handleRoleChange, t]
  );

  const table = useReactTable({
    data: users,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (isLoading) {
    return (
      <Flex justifyContent='center' alignItems='center' style={{ height: '80vh' }}>
        <LoadingSpinner size='large' />
      </Flex>
    );
  }

  return (
    <Flex flexDirection='column' gap='4' className='p-8 h-full overflow-auto'>
      <Flex justifyContent='space-between' alignItems='center'>
        <Typography variant='h2'>{t('User Administration')}</Typography>
      </Flex>

      <div className='glass-panel p-4 mb-2'>
        <Typography variant='body-medium' className='mb-2'>
          {t('Register New User')}
        </Typography>
        <Flex gap='4' alignItems='end' flexWrap='wrap'>
          <TextInput
            onChange={(e) => setNewUserEmail(e.target.value)}
            value={newUserEmail}
            htmlAttributes={{ type: 'email', placeholder: t('Enter user email address') }}
            className='flex-1'
            style={{ minWidth: '220px' }}
          />
          <div style={{ width: '180px' }}>
            <PremiumDropdown
              value={newUserRole}
              options={roles.map((r) => ({ label: r, value: r }))}
              onChange={(v: string) => {
                setNewUserRole(v);
                setNewUserCaseId('');
              }}
            />
          </div>
          {newUserRole === 'Patient' && newUserEmail.includes('@') && (
            <div style={{ display: 'flex', flexDirection: 'column', minWidth: '180px' }}>
              <label style={{ fontSize: '11px', opacity: 0.6, marginBottom: '4px' }}>
                {t('Case ID')} <span style={{ opacity: 0.5 }}>({t('optional — auto-generated if blank')})</span>
              </label>
              <TextInput
                onChange={(e) => setNewUserCaseId(e.target.value)}
                value={newUserCaseId}
                htmlAttributes={{ placeholder: t('e.g. PT-001'), maxLength: 32 }}
              />
            </div>
          )}
          <Button onClick={handleCreateUser} isDisabled={isAddingUser || !newUserEmail}>
            {t('Add User')}
          </Button>
        </Flex>

        {newUserRole === 'Patient' && (
          <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px', opacity: 0.6 }}>
            <RiLockLine size={12} />
            <Typography variant='body-small'>
              {t('Once a Case ID is assigned to a patient, it cannot be changed.')}
            </Typography>
          </div>
        )}
      </div>

      {alert && (
        <Banner type={alert.type} onClose={() => setAlert(null)} isCloseable={true} className='mb-4'>
          {alert.message}
        </Banner>
      )}

      <div className='glass-panel p-4 mb-8 h-fit'>
        {/* @ts-ignore */}
        <DataGrid
          tableInstance={table}
          styling={{
            borderStyle: 'all-sides',
            hasZebraStriping: true,
            headerStyle: 'clean',
          }}
          components={{
            Body: () => <DataGridComponents.Body />,
            Pagination: () => <></>,
          }}
        />
      </div>

      <Typography variant='h2' className='mt-4'>
        {t('Translation Management')}
      </Typography>
      <div className='glass-panel p-4 mb-4'>
        <div className='flex items-end gap-4 mb-4 flex-wrap'>
          <div style={{ width: '220px' }}>
            <Typography variant='body-small' className='mb-2 block opacity-70'>
              {t('Seed Language')}
            </Typography>
            <PremiumDropdown
              value={seedLanguage}
              options={SUPPORTED_LANGUAGES.filter((lang) => lang.code !== 'en').map((lang) => ({
                label: `${lang.code.toUpperCase()} - ${lang.nameEn}`,
                value: lang.code,
                description: lang.name,
              }))}
              onChange={(value: string) => setSeedLanguage(value)}
            />
          </div>
          <Button onClick={handleSeedTranslations} isDisabled={isSeedingTranslations}>
            {isSeedingTranslations ? t('Seeding...') : t('Seed Translations')}
          </Button>
          <Button onClick={() => fetchData()} fill='outlined' isDisabled={isSeedingTranslations}>
            {t('Refresh Statistics')}
          </Button>
        </div>
        <table className='w-full text-left text-sm'>
          <thead>
            <tr className='border-b opacity-60'>
              <th className='py-2'>{t('Language')}</th>
              <th>{t('Coverage')}</th>
              <th>{t('Untranslated')}</th>
            </tr>
          </thead>
          <tbody>
            {transStats.map((s) => (
              <tr key={s.lang} className='border-b last:border-none'>
                <td className='py-3 font-bold'>{s.lang.toUpperCase()}</td>
                <td>
                  <div className='flex items-center gap-2'>
                    <div className='bg-neutral-200 h-2 w-24 rounded-full overflow-hidden'>
                      <div className='bg-green-500 h-full' style={{ width: `${s.coverage}%` }} />
                    </div>
                    {(s.coverage ?? 0).toFixed(1)}%
                  </div>
                </td>
                <td>{s.total - s.translated}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Flex>
  );
};

export default AdminPage;
