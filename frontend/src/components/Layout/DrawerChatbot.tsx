import { Drawer } from '@neo4j-ndl/react';
import Chatbot from '../ChatBot/Chatbot';
import { Messages } from '../../types';
import ExpandedChatButtonContainer from '../ChatBot/ExpandedChatButtonContainer';
import { useMessageContext } from '../../context/UserMessages';
import { useLocation } from 'react-router';
import { useEffect } from 'react';
import { useCredentials } from '../../context/UserCredentials';

export interface DrawerChatbotProps {
  isExpanded: boolean;
  clearHistoryData: boolean;
  messages: Messages[];
  connectionStatus: boolean;
  isFullScreen?: boolean;
  toggleFullScreen?: () => void;
  closeChatBot?: () => void;
}

const DrawerChatbot: React.FC<DrawerChatbotProps> = ({
  isExpanded,
  clearHistoryData,
  messages,
  connectionStatus,
  isFullScreen,
  toggleFullScreen,
  closeChatBot,
}) => {
  const { setMessages, isDeleteChatLoading } = useMessageContext();
  const { setUserCredentials, setIsGCSActive, setGdsActive, setIsReadOnlyUser } = useCredentials();
  const location = useLocation();

  useEffect(() => {
    // const localStorageData = localStorage.getItem('neo4j.connection');
    // const connectionLocal = JSON.parse(localStorageData ?? '');
    // if (connectionStatus && (connectionLocal.uri === userCredentials?.uri)) {
    if (connectionStatus) {
      if (location && location.state && Array.isArray(location.state)) {
        setMessages(location.state);
      } else if (
        location &&
        location.state &&
        typeof location.state === 'object' &&
        Object.keys(location.state).length > 1
      ) {
        setUserCredentials(location.state.credential);
        setIsGCSActive(location.state.isGCSActive);
        setGdsActive(location.state.isgdsActive);
        setIsReadOnlyUser(location.state.isReadOnlyUser);
      }
    }
  }, [location, connectionStatus]);

  const getIsLoading = (messages: Messages[]) => {
    return messages.length > 1 ? messages.some((msg) => msg.isTyping || msg.isLoading) : false;
  };
  return (
    <div className='flex min-h-[calc(-58px+100vh)] relative w-full'>
      <Drawer isExpanded={isExpanded} isCloseable={false} position='left' type='push' className='pt-0!'>
        <Drawer.Body className='overflow-hidden! pr-0!'>
          <div className='flex flex-row w-full h-full p-2 gap-4'>
            <ExpandedChatButtonContainer
              closeChatBot={closeChatBot || (() => {})}
              deleteOnClick={() => setMessages([])}
              messages={messages}
              isFullScreen={isFullScreen}
              toggleFullScreen={toggleFullScreen}
            />
            <div className='flex-1 min-w-0 relative'>
              <Chatbot
                isFullScreen={false}
                messages={messages}
                setMessages={setMessages}
                clear={clearHistoryData}
                isLoading={getIsLoading(messages)}
                connectionStatus={connectionStatus}
                isDeleteChatLoading={isDeleteChatLoading}
              />
            </div>
          </div>
        </Drawer.Body>
      </Drawer>
    </div>
  );
};
export default DrawerChatbot;
