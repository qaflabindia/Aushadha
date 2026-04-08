import React, { useState } from 'react';
import { Drawer, Typography, TextInput, Button, Flex } from '@neo4j-ndl/react';
import { RiFlaskLine } from 'react-icons/ri';
import { useFileContext } from '../../context/UsersFiles';
import { chatModeLables } from '../../utils/Constants';

interface ResearchDrawerProps {
  isExpanded: boolean;
  toggleRightDrawer: () => void;
}

const ResearchDrawer: React.FC<ResearchDrawerProps> = ({ isExpanded, toggleRightDrawer }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const { setchatModes } = useFileContext();

  const handleSearch = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!searchQuery.trim()) {
      return;
    }

    // Set the chat mode to AYUSH Clinical
    setchatModes([chatModeLables['ayush clinical']]);

    // Dispatch custom event to trigger chatbot
    const event = new CustomEvent('external-chat-query', {
      detail: { query: searchQuery },
    });
    window.dispatchEvent(event);

    // Open the right drawer
    toggleRightDrawer();
    setSearchQuery('');
  };

  return (
    <div className='flex relative min-h-[calc(-58px+100vh)]'>
      <Drawer isExpanded={isExpanded} position='left' type='push' isCloseable={false}>
        <Drawer.Body className='overflow-hidden! w-[294px]! p-6'>
          <Flex flexDirection='column' gap='6' className='h-full'>
            <div className='flex flex-col gap-2'>
              <div className='flex items-center gap-2 text-[#D4AF37]'>
                <RiFlaskLine size={24} />
                <Typography variant='h3' className='font-bold tracking-tight text-[#D4AF37]!'>
                  Live Research
                </Typography>
              </div>
              <Typography variant='body-small' className='opacity-60'>
                Explore AYUSH government and research databases for real-time clinical intelligence.
              </Typography>
            </div>

            <form onSubmit={handleSearch} className='flex flex-col gap-4'>
              <TextInput
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder='Search clinical data...'
                isFluid
              />
              <Button
                onClick={handleSearch}
                className='w-full font-bold uppercase tracking-widest text-[10px] shadow-lg'
                fill='filled'
              >
                Start Intelligence Search
              </Button>
            </form>

            <div className='mt-auto p-4 rounded-xl bg-[#D4AF37]/5 border border-[#D4AF37]/10'>
              <Typography variant='body-small' className='text-[#D4AF37]/60 italic'>
                "Harnessing ancient wisdom through modern neural architectures."
              </Typography>
            </div>
          </Flex>
        </Drawer.Body>
      </Drawer>
    </div>
  );
};

export default ResearchDrawer;
