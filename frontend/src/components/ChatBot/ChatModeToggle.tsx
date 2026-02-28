import { StatusIndicator, Typography } from '@neo4j-ndl/react';
import { useFileContext } from '../../context/UsersFiles';
import CustomMenu from '../UI/CustomMenu';
import { chatModeLables, chatModes as AvailableModes, chatModeReadableLables } from '../../utils/Constants';
import { capitalize } from '@mui/material';
import { capitalizeWithPlus } from '../../utils/Utils';
import { useCredentials } from '../../context/UserCredentials';
import { useGoogleAuth } from '../../context/GoogleAuthContext';
import { JSXElementConstructor, ReactElement, ReactNode, ReactPortal, useContext, useMemo } from 'react';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';

export default function ChatModeToggle({
  menuAnchor,
  closeHandler = () => {},
  open,
  isRoot,
}: {
  menuAnchor: React.RefObject<HTMLElement | null>;
  closeHandler?: (
    event: Event | undefined,
    closeReason: {
      type: 'backdropClick' | 'itemClick' | 'escapeKeyDown';
      id?: string;
    }
  ) => void;
  open: boolean;
  isRoot: boolean;
}) {
  const { setchatModes, chatModes, postProcessingTasks } = useFileContext();
  const isCommunityAllowed = postProcessingTasks.includes('enable_communities');
  const { isGdsActive } = useCredentials();
  const { colorMode } = useContext(ThemeWrapperContext);
  const { user } = useGoogleAuth();

  const textColor = colorMode === 'dark' ? '#D4AF37' : '#1A1A1A';
  const descriptionColor = colorMode === 'dark' ? 'rgba(212,175,55,0.7)' : '#555555';

  if (!chatModes.length) {
    setchatModes([chatModeLables['graph+vector+fulltext']]);
  }

  const memoizedChatModes = useMemo(() => {
    let filtered = AvailableModes;
    if (!(isGdsActive && isCommunityAllowed)) {
      filtered = filtered?.filter(
        (m: { mode: string }) => !m.mode.includes(chatModeLables['global search+vector+fulltext'])
      );
    }
    // Only Admin, Doctor, and Staff can see AYUSH Clinical mode
    if (!(user?.role === 'Admin' || user?.role === 'Doctor' || user?.role === 'Staff')) {
      filtered = filtered?.filter((m: { mode: string }) => m.mode !== chatModeLables['ayush clinical']);
    }
    return filtered;
  }, [isGdsActive, isCommunityAllowed, user?.role]);

  const menuItems = useMemo(() => {
    return memoizedChatModes?.map(
      (
        m: {
          mode: string;
          description:
            | string
            | number
            | boolean
            | ReactElement<any, string | JSXElementConstructor<any>>
            | Iterable<ReactNode>
            | ReactPortal
            | null
            | undefined;
        },
        index: any
      ) => {
        const isAyush = m.mode === chatModeLables['ayush clinical'];
        const handleModeChange = () => {
          if (chatModes.includes(m.mode)) {
            if (chatModes.length === 1) {
              return;
            }
            setchatModes((prev: string[]) => prev.filter((i: string) => i !== m.mode));
          } else {
            setchatModes((prev: string[]) => [...prev, m.mode]);
          }
        };
        return {
          id: m.mode || `menu-item-${index}`,
          title: (
            <div style={{ color: textColor }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {isAyush && (
                  <span
                    style={{
                      fontSize: '8px',
                      fontWeight: 800,
                      letterSpacing: '0.15em',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: colorMode === 'dark' ? 'rgba(212,175,55,0.15)' : '#e6f4ea',
                      color: colorMode === 'dark' ? '#D4AF37' : '#1a7340',
                      border: `1px solid ${colorMode === 'dark' ? 'rgba(212,175,55,0.3)' : '#a8d5b5'}`,
                      textTransform: 'uppercase' as const,
                    }}
                  >
                    LIVE
                  </span>
                )}
                <Typography variant='subheading-small' style={{ color: textColor }}>
                  {chatModeReadableLables[m.mode].includes('+')
                    ? capitalizeWithPlus(chatModeReadableLables[m.mode])
                    : capitalize(chatModeReadableLables[m.mode])}
                </Typography>
              </div>
              <div>
                <Typography variant='body-small' style={{ color: descriptionColor }}>
                  {m.description}
                </Typography>
              </div>
            </div>
          ),
          onClick: (e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
            handleModeChange();
            e.stopPropagation();
          },
          disabledCondition: false,
          description: (
            <span>
              {chatModes.includes(m.mode) && (
                <>
                  <StatusIndicator type='success' /> {chatModeLables.selected}
                </>
              )}
            </span>
          ),
        };
      }
    );
  }, [chatModes, memoizedChatModes, textColor, descriptionColor, colorMode]);

  return (
    <CustomMenu isRoot={isRoot} closeHandler={closeHandler} open={open} anchorOrigin={menuAnchor} items={menuItems} />
  );
}
