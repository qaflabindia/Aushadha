import React, { useState } from 'react';
import { Tabs, Flex, useMediaQuery } from '@neo4j-ndl/react';
import { tokens } from '@neo4j-ndl/base';
import { useTranslation } from '../../context/LanguageContext';
import { useFileContext } from '../../context/UsersFiles';
import NewEntityExtractionSetting from '../Popups/GraphEnhancementDialog/EnitityExtraction/NewEntityExtractionSetting';
import AdditionalInstructionsText from '../Popups/GraphEnhancementDialog/AdditionalInstructions';
import DeletePopUpForOrphanNodes from '../Popups/GraphEnhancementDialog/DeleteTabForOrphanNodes';
import DeduplicationTab from '../Popups/GraphEnhancementDialog/Deduplication';
import PostProcessingCheckList from '../Popups/GraphEnhancementDialog/PostProcessingCheckList';
import deleteOrphanAPI from '../../services/DeleteOrphanNodes';
import { OptionType } from '../../types';

interface GraphSettingsTabsProps {
  combinedPatterns: string[];
  setCombinedPatterns: React.Dispatch<React.SetStateAction<string[]>>;
  combinedNodes: OptionType[];
  setCombinedNodes: React.Dispatch<React.SetStateAction<OptionType[]>>;
  combinedRels: OptionType[];
  setCombinedRels: React.Dispatch<React.SetStateAction<OptionType[]>>;
}

const GraphSettingsTabs: React.FC<GraphSettingsTabsProps> = ({
  combinedPatterns,
  setCombinedPatterns,
  combinedNodes,
  setCombinedNodes,
  combinedRels,
  setCombinedRels,
}) => {
  const { breakpoints } = tokens;
  const isTablet = useMediaQuery(`(min-width:${breakpoints.xs}) and (max-width: ${breakpoints.lg})`);
  const t = useTranslation();
  const [activeTab, setActiveTab] = useState<number>(0);
  const [orphanDeleteLoading, setOrphanDeleteLoading] = useState(false);

  const { setShowTextFromSchemaDialog, setSchemaLoadDialog, setPredefinedSchemaDialog, setDataImporterSchemaDialog } =
    useFileContext();

  const handleOrphanDelete = async (selectedEntities: string[]) => {
    try {
      setOrphanDeleteLoading(true);
      await deleteOrphanAPI(selectedEntities);
    } catch (error) {
      console.error('Failed to delete orphan nodes:', error);
    } finally {
      setOrphanDeleteLoading(false);
    }
  };

  const noop = () => {};

  return (
    <Flex flexDirection='column' gap='6' className='w-full'>
      <Tabs fill='underline' onChange={setActiveTab} size={isTablet ? 'small' : 'large'} value={activeTab}>
        <Tabs.Tab tabId={0}>{t('entityExtractionSettings') || 'Extraction'}</Tabs.Tab>
        <Tabs.Tab tabId={1}>{t('additionalInstructions') || 'Instructions'}</Tabs.Tab>
        <Tabs.Tab tabId={2}>{t('disconnectedNodes') || 'Cleaning'}</Tabs.Tab>
        <Tabs.Tab tabId={3}>{t('duplicationNodes') || 'Deduplication'}</Tabs.Tab>
        <Tabs.Tab tabId={4}>{t('postProcessingJobs') || 'Jobs'}</Tabs.Tab>
      </Tabs>

      <div className='min-h-[400px]'>
        {activeTab === 0 && (
          <div className='animate-fade-in'>
            <NewEntityExtractionSetting
              view='Tabs'
              openTextSchema={() => setShowTextFromSchemaDialog({ triggeredFrom: 'enhancementtab', show: true })}
              openLoadSchema={() => setSchemaLoadDialog({ triggeredFrom: 'enhancementtab', show: true })}
              openPredefinedSchema={() => setPredefinedSchemaDialog({ triggeredFrom: 'enhancementtab', show: true })}
              openDataImporterSchema={() =>
                setDataImporterSchemaDialog({ triggeredFrom: 'enhancementtab', show: true })
              }
              closeEnhanceGraphSchemaDialog={noop}
              settingView='headerView'
              combinedPatterns={combinedPatterns}
              setCombinedPatterns={setCombinedPatterns}
              combinedNodes={combinedNodes}
              setCombinedNodes={setCombinedNodes}
              combinedRels={combinedRels}
              setCombinedRels={setCombinedRels}
            />
          </div>
        )}

        {activeTab === 1 && (
          <div className='animate-fade-in'>
            <AdditionalInstructionsText closeEnhanceGraphSchemaDialog={noop} />
          </div>
        )}

        {activeTab === 2 && (
          <div className='animate-fade-in'>
            <DeletePopUpForOrphanNodes deleteHandler={handleOrphanDelete} loading={orphanDeleteLoading} />
          </div>
        )}

        {activeTab === 3 && (
          <div className='animate-fade-in'>
            <DeduplicationTab />
          </div>
        )}

        {activeTab === 4 && (
          <div className='animate-fade-in'>
            <PostProcessingCheckList />
          </div>
        )}
      </div>
    </Flex>
  );
};

export default GraphSettingsTabs;
