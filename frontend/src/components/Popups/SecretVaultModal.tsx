import React, { useState, useEffect } from 'react';
import { Button, Dialog, TextInput, Typography, Banner } from '@neo4j-ndl/react';
import { LockClosedIconOutline } from '@neo4j-ndl/react/icons';
import { getSecrets, saveSecret } from '../../services/SecretAPI';

interface SecretVaultModalProps {
  open: boolean;
  onClose: () => void;
}

const SecretVaultModal: React.FC<SecretVaultModalProps> = ({ open, onClose }) => {
  const [secretName, setSecretName] = useState('');
  const [secretValue, setSecretValue] = useState('');
  const [status, setStatus] = useState<{ type: 'success' | 'danger'; message: string } | null>(null);
  const [existingSecrets, setExistingSecrets] = useState<string[]>([]);

  useEffect(() => {
    if (open) {
      fetchSecrets();
    }
  }, [open]);

  const fetchSecrets = async () => {
    try {
      const response = await getSecrets();
      if (response.data.status === 'Success') {
        setExistingSecrets(response.data.data);
      }
    } catch (error) {
      console.error('Error fetching secrets:', error);
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
    } catch (error) {
      setStatus({ type: 'danger', message: 'Network error.' });
    }
  };

  return (
    <Dialog isOpen={open} onClose={onClose} size='small' modalProps={{ className: 'ndl-dialog' }}>
      <Dialog.Header>
        <div className='flex items-center gap-2'>
          <LockClosedIconOutline className='n-size-token-7 text-[#D4AF37]' />
          <Typography variant='h3' className='!text-[#D4AF37] font-bold'>
            Secret Vault
          </Typography>
        </div>
      </Dialog.Header>
      <Dialog.Content className='flex flex-col gap-6'>
        <Typography variant='body-medium' className='!text-white opacity-90'>
          Store your API keys securely in the encrypted vault. These will be used by the backend as overrides for
          environment variables.
        </Typography>

        {status && (
          <Banner type={status.type} isCloseable onClose={() => setStatus(null)} className='shadow-lg'>
            {status.message}
          </Banner>
        )}

        <div className='space-y-4'>
          <div className='space-y-1'>
            <label className='high-contrast-label px-1'>Secret Name</label>
            <TextInput
              value={secretName}
              onChange={(e) => setSecretName(e.target.value)}
              placeholder='e.g. OPENAI_API_KEY'
              isFluid
            />
          </div>
          <div className='space-y-1'>
            <label className='high-contrast-label px-1'>Secret Value</label>
            <TextInput
              htmlAttributes={{ type: 'password' }}
              value={secretValue}
              onChange={(e) => setSecretValue(e.target.value)}
              placeholder='••••••••••••••••'
              isFluid
            />
          </div>
        </div>

        <div className='mt-2 text-right'>
          <Button onClick={handleSave} className='ndl-button-primary'>
            Save Secret
          </Button>
        </div>

        <div className='mt-4 pt-4 border-t border-[#D4AF37]/20'>
          <Typography variant='subheading-medium' className='!text-[#D4AF37] mb-3 uppercase tracking-wider text-xs'>
            Configured Secrets
          </Typography>
          <div className='flex flex-wrap gap-2 mt-2'>
            {existingSecrets.length > 0 ? (
              existingSecrets.map((key) => (
                <div
                  key={key}
                  className='luxury-tag px-3 py-1.5 rounded-full flex items-center gap-2 border border-[#D4AF37]/30 bg-[#D4AF37]/10'
                >
                  <Typography variant='body-small' className='font-bold tracking-tight'>
                    {key}
                  </Typography>
                  <LockClosedIconOutline className='n-size-token-4 text-[#D4AF37]' />
                </div>
              ))
            ) : (
              <Typography variant='body-small' className='text-gray-500 italic'>
                No secrets configured yet.
              </Typography>
            )}
          </div>
        </div>
      </Dialog.Content>
      <Dialog.Actions>
        <Button onClick={onClose} fill='text' className='!text-gray-400 hover:!text-white'>
          Close
        </Button>
      </Dialog.Actions>
    </Dialog>
  );
};

export default SecretVaultModal;
