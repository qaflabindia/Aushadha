import { useMemo, useRef, useState, useCallback, useEffect } from 'react';
import { Menu, Typography, Avatar } from '@neo4j-ndl/react';
import { ChevronDownIconOutline } from '@neo4j-ndl/react/icons';
import { useGoogleAuth } from '../../context/GoogleAuthContext';
import { getTokenLimits, TokenLimitsResponse } from '../../services/TokenLimits';
import { useCredentials } from '../../context/UserCredentials';
import { isNeo4jUser } from '../../utils/Utils';
import { useTranslate } from '../../context/TranslationContext';

export default function Profile() {
  const [showMenu, setShowOpen] = useState<boolean>(false);
  const [tokenLimits, setTokenLimits] = useState<TokenLimitsResponse | null>(null);
  const [isLoadingTokens, setIsLoadingTokens] = useState<boolean>(false);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const iconbtnRef = useRef<HTMLButtonElement | null>(null);
  const { user, isAuthenticated, isLoading, logout } = useGoogleAuth();
  const { userCredentials, connectionStatus } = useCredentials();
  const t = useTranslate();

  const fetchTokenLimits = useCallback(async () => {
    if (!userCredentials?.uri && !userCredentials?.email) {
      setTokenError('User credentials not available');
      return;
    }
    setIsLoadingTokens(true);
    setTokenError(null);
    try {
      const limits = await getTokenLimits(userCredentials);
      if (limits) {
        setTokenLimits(limits);
        setTokenError(null);
      } else {
        setTokenLimits(null);
      }
    } catch (error) {
      setTokenError(t('Error loading token limits'));
      setTokenLimits(null);
    } finally {
      setIsLoadingTokens(false);
    }
  }, [userCredentials, t]);

  useEffect(() => {
    if (isAuthenticated && connectionStatus) {
      fetchTokenLimits();
    }
  }, [isAuthenticated, connectionStatus, fetchTokenLimits]);

  const settings = useMemo(() => {
    const isNeo4j = isNeo4jUser(user?.email);

    const getDailyTokensTitle = () => {
      if (isLoadingTokens) {
        return t('Daily Tokens Used: Loading...');
      }
      if (!connectionStatus) {
        return t('Daily Tokens Used: No DB connection');
      }
      if (tokenError) {
        return t('Daily Tokens Used: N/A');
      }
      const used = tokenLimits?.daily_used.toLocaleString() ?? t('N/A');
      if (isNeo4j) {
        return `${t('Daily Tokens Used:')} ${used}`;
      }
      const limit = tokenLimits?.daily_limit.toLocaleString() ?? t('N/A');
      return `${t('Daily Tokens Used:')} ${used} / ${limit}`;
    };

    const getMonthlyTokensTitle = () => {
      if (isLoadingTokens) {
        return t('Monthly Tokens: Loading...');
      }
      if (!connectionStatus) {
        return t('Monthly Tokens Used: No DB connection');
      }
      if (tokenError) {
        return t('Monthly Tokens Used: N/A');
      }
      const used = tokenLimits?.monthly_used.toLocaleString() ?? t('N/A');
      if (isNeo4j) {
        return `${t('Monthly Tokens Used:')} ${used}`;
      }
      const limit = tokenLimits?.monthly_limit.toLocaleString() ?? t('N/A');
      return `${t('Monthly Tokens Used:')} ${used} / ${limit}`;
    };

    const tokenItems = [
      {
        title: getDailyTokensTitle(),
        onClick: () => {},
        disabled: true,
      },
      {
        title: getMonthlyTokensTitle(),
        onClick: () => {},
        disabled: true,
      },
      {
        title: t('Get Latest Usage'),
        onClick: () => {
          fetchTokenLimits();
        },
        disabled: isLoadingTokens,
      },
    ];

    return [
      ...tokenItems,
      {
        title: t('Logout'),
        onClick: () => {
          logout();
          window.location.href = '/login';
        },
      },
    ];
  }, [tokenLimits, isLoadingTokens, tokenError, fetchTokenLimits, logout, user?.email, connectionStatus, t]);

  const handleClick = () => {
    setShowOpen(true);
  };
  const handleClose = useCallback(() => {
    setShowOpen(false);
  }, []);

  if (isLoading) {
    return <Avatar></Avatar>;
  }
  if (isAuthenticated) {
    return (
      <div
        className='p-1.5 h-12 profile-container cursor-pointer hover:bg-white/5 rounded-lg transition-colors flex items-center gap-3'
        onClick={handleClick}
        ref={iconbtnRef as any}
      >
        <Avatar
          className='md:flex hidden'
          name={user?.name?.charAt(0).toLocaleUpperCase()}
          size='large'
          type='letters'
          shape='square'
        />
        <div className='flex flex-col'>
          <Typography variant='body-medium' className='p-0.5 leading-none'>
            {user?.name?.split('@')[0] ?? 'John Doe'}
          </Typography>

          <Typography variant='body-small' className='p-0.5 leading-none opacity-60'>
            {user?.email ?? 'john.doe@neo4j.com'}
          </Typography>
        </div>
        <ChevronDownIconOutline className='w-4 h-4 opacity-40' />
        <Menu anchorRef={iconbtnRef} isOpen={showMenu} onClose={handleClose}>
          <Menu.Items>
            {settings.map((setting, index) => (
              <Menu.Item
                key={`${setting.title}-${index}`}
                onClick={() => !('disabled' in setting && setting.disabled) && setting.onClick()}
                title={setting.title}
                isDisabled={'disabled' in setting ? setting.disabled : false}
              />
            ))}
          </Menu.Items>
        </Menu>
      </div>
    );
  }
  return null;
}
