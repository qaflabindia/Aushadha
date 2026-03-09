import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { 
  Typography, 
  DataGrid, 
  DataGridComponents,
  Flex, 
  LoadingSpinner, 
  Banner,
  Button,
  TextInput
} from '@neo4j-ndl/react';
import { 
  useReactTable, 
  getCoreRowModel, 
  createColumnHelper 
} from '@tanstack/react-table';
import { useGoogleAuth } from '../../context/GoogleAuthContext';
import { useTranslate } from '../../context/TranslationContext';
import axios from 'axios';
import { PremiumDropdown } from '../UI/PremiumDropdown';

interface UserRecord {
  id: number;
  email: string;
  role: string;
  created_at: string;
}

const AdminPage: React.FC<{ embedded?: boolean }> = ({ embedded: _embedded = false }) => {
  const { getAuthHeaders, user: currentUser } = useGoogleAuth();
  const t = useTranslate();
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [alert, setAlert] = useState<{ type: 'success' | 'danger', message: string } | null>(null);

  const [isAddingUser, setIsAddingUser] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserRole, setNewUserRole] = useState('Patient');

  const apiBase = import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000';
  const columnHelper = createColumnHelper<UserRecord>();

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const headers = getAuthHeaders();
      const [usersRes, rolesRes] = await Promise.all([
        axios.get(`${apiBase}/rbac/users`, { headers }),
        axios.get(`${apiBase}/rbac/roles`, { headers })
      ]);
      setUsers(usersRes.data);
      setRoles(rolesRes.data);
    } catch (err) {
      console.error('Failed to fetch admin data', err);
      setAlert({ type: 'danger', message: t('Failed to load user management data.') });
    } finally {
      setIsLoading(false);
    }
  }, [apiBase, getAuthHeaders]);

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
      await axios.post(`${apiBase}/rbac/assign_role`, { email: newUserEmail.toLowerCase(), role_name: newUserRole }, { headers });
      setAlert({ type: 'success', message: `${t('Successfully registered')} ${newUserEmail} ${t('as')} ${newUserRole}` });
      setNewUserEmail('');
      fetchData();
    } catch (err) {
      console.error('Failed to create user', err);
      setAlert({ type: 'danger', message: `${t('Failed to create user')} ${newUserEmail}` });
    } finally {
      setIsAddingUser(false);
    }
  };

  const handleRoleChange = useCallback(async (email: string, newRole: string) => {
    try {
      const headers = getAuthHeaders();
      await axios.post(`${apiBase}/rbac/assign_role`, { email, role_name: newRole }, { headers });
      setAlert({ type: 'success', message: `${t('Successfully assigned')} ${newRole} ${t('to')} ${email}` });
      fetchData();
    } catch (err) {
      console.error('Failed to assign role', err);
      setAlert({ type: 'danger', message: `${t('Failed to assign role to')} ${email}` });
    }
  }, [apiBase, getAuthHeaders, fetchData, t]);

  const columns = useMemo(() => [
    columnHelper.accessor('email', {
      header: t('Email'),
      cell: (info) => <Typography variant="body-medium">{info.getValue()}</Typography>,
    }),
    columnHelper.accessor('role', {
      header: t('Current Role'),
      cell: (info) => {
        const email = info.row.original.email;
        const currentRole = info.getValue();
        
        return (
          <div style={{ width: '220px' }}>
            <PremiumDropdown
              value={currentRole || 'None'}
              options={roles.map(r => ({ label: r, value: r }))}
              onChange={(newValue: string) => handleRoleChange(email, newValue)}
              disabled={email === currentUser?.email}
            />
          </div>
        );
      }
    }),
    columnHelper.accessor('created_at', {
      header: t('Joined'),
      cell: (info) => (
        <Typography variant="body-small">
          {new Date(info.getValue()).toLocaleDateString()}
        </Typography>
      ),
    })
  ], [roles, currentUser, handleRoleChange, t]);

  const table = useReactTable({
    data: users,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (isLoading) {
    return (
      <Flex justifyContent="center" alignItems="center" style={{ height: '80vh' }}>
        <LoadingSpinner size="large" />
      </Flex>
    );
  }

  return (
    <Flex flexDirection="column" gap="4" className="p-8 h-full overflow-auto">
      <Flex justifyContent="space-between" alignItems="center">
        <Typography variant="h2">{t('User Administration')}</Typography>
      </Flex>
      
      <div className="glass-panel p-4 mb-2 flex items-end gap-4">
        <div className="flex-1">
          <Typography variant="body-medium" className="mb-2">{t('Register New User')}</Typography>
          <Flex gap="4" alignItems="end">
            <TextInput
              onChange={(e) => setNewUserEmail(e.target.value)}
              value={newUserEmail}
              htmlAttributes={{ type: 'email', placeholder: t("Enter user email address") }}
              className="flex-1"
            />
            <div style={{ width: '220px' }}>
              <PremiumDropdown
                value={newUserRole}
                options={roles.map(r => ({ label: r, value: r }))}
                onChange={(v: string) => setNewUserRole(v)}
              />
            </div>
            <Button 
              onClick={handleCreateUser} 
              isDisabled={isAddingUser || !newUserEmail}
            >
              {t('Add User')}
            </Button>
          </Flex>
        </div>
      </div>
      
      {alert && (
        <Banner 
          type={alert.type} 
          onClose={() => setAlert(null)}
          isCloseable={true}
          className="mb-4"
        >
          {alert.message}
        </Banner>
      )}

      <div className="glass-panel p-4 flex-1">
        {/* @ts-ignore */}
        <DataGrid
          tableInstance={table}
          styling={{
            borderStyle: 'all-sides',
            hasZebraStriping: true,
            headerStyle: 'clean',
          }}
          components={{
            Body: () => (
              <DataGridComponents.Body />
            ),
            Pagination: () => <></>
          }}
        />
      </div>
    </Flex>
  );
};

export default AdminPage;
