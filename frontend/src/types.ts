import { AlertColor, AlertPropsColorOverrides } from '@mui/material';
import React, { Dispatch, ReactNode, SetStateAction } from 'react';
import { OverridableStringUnion } from '@mui/types';
import type { Node, Relationship } from '@neo4j-nvl/base';
import { BannerType } from '@neo4j-ndl/react';

export interface CustomFileBase extends Partial<globalThis.File> {
  processingTotalTime: number | string;
  status: string;
  nodesCount: number;
  relationshipsCount: number;
  model: string;
  fileSource: string;
  sourceUrl?: string;
  wikiQuery?: string;
  gcsBucket?: string;
  gcsBucketFolder?: string;
  errorMessage?: string;
  uploadProgress?: number;
  processingStatus?: boolean;
  googleProjectId?: string;
  language?: string;
  processingProgress?: number;
  accessToken?: string;
  isChecked?: boolean;
  retryOptionStatus: boolean;
  retryOption: string;
  chunkNodeCount: number;
  chunkRelCount: number;
  entityNodeCount: number;
  entityEntityRelCount: number;
  communityNodeCount: number;
  communityRelCount: number;
  createdAt?: Date;
}
export interface CustomFile extends CustomFileBase {
  id: string;
}

export interface OptionType {
  readonly value: string;
  readonly label: string;
}

export type UserCredentials = {
  uri?: string;
  userName?: string;
  password?: string;
  database?: string;
  email?: string;
  target_user_email?: string;
  connection?: string;
} & { [key: string]: any };

export interface SourceNode extends Omit<CustomFileBase, 'relationshipsCount' | 'createdAt'> {
  fileName: string;
  fileSize: number;
  fileType: string;
  nodeCount?: number;
  processingTime: string;
  relationshipCount?: number;
  url?: string;
  awsAccessKeyId?: string;
  uploadprogress?: number;
  gcsProjectId?: string;
  processed_chunk?: number;
  total_chunks?: number;
  retry_condition?: string;
  createdAt: filedate;
}

export type ExtractParams = Pick<CustomFile, 'wikiQuery' | 'model' | 'sourceUrl' | 'language' | 'accessToken'> & {
  file?: File;
  aws_access_key_id?: string | null;
  aws_secret_access_key?: string | null;
  gcs_bucket_name?: string;
  gcs_bucket_folder?: string;
  gcs_blob_filename?: string;
  source_type?: string;
  file_name?: string;
  allowedNodes?: string[];
  allowedRelationship?: string[];
  gcs_project_id?: string;
  retry_condition: string;
  additional_instructions?: string;
} & { [key: string]: any };

export type UploadParams = {
  file: Blob;
  model: string;
  chunkNumber: number;
  totalChunks: number;
  originalname: string;
} & { [key: string]: any };

export type FormDataParams = ExtractParams | UploadParams;

export interface DropdownProps {
  onSelect: (option: OptionType | null | void) => void;
}

export interface CustomAlertProps {
  open: boolean;
  handleClose: () => void;
  alertMessage: string;
  severity?: OverridableStringUnion<AlertColor, AlertPropsColorOverrides> | undefined;
}
export interface DataComponentProps {
  openModal: () => void;
  isLargeDesktop?: boolean;
  isDisabled?: boolean;
}
export interface S3ModalProps {
  hideModal: () => void;
  open: boolean;
}
export interface GCSModalProps extends Omit<S3ModalProps, ''> {
  openGCSModal: () => void;
}

export type DrawerMode = 'upload' | 'research' | 'admin' | 'settings';

export interface SideNavProps {
  toggleLeftDrawer: () => void;
  toggleRightDrawer: () => void;
  isLeftExpanded: boolean;
  isRightExpanded: boolean;
  deleteOnClick?: () => void;
  setShowDrawerChatbot?: Dispatch<SetStateAction<boolean>>;
  showDrawerChatbot?: boolean;
  messages?: Messages[];
  clearHistoryData?: boolean;
  toggles3Modal?: () => void;
  toggleGCSModal?: () => void;
  toggleGenericModal?: () => void;
  setIsleftExpanded?: Dispatch<SetStateAction<boolean>>;
  activeDrawerMode: DrawerMode;
  setActiveDrawerMode: (mode: DrawerMode) => void;
}

export interface DrawerProps {
  isExpanded: boolean;
  shows3Modal: boolean;
  showGCSModal: boolean;
  showGenericModal: boolean;
  toggleS3Modal: () => void;
  toggleGCSModal: () => void;
  toggleGenericModal: () => void;
}

export interface ContentProps {
  showChatBot: boolean;
  openChatBot: () => void;
  openTextSchema: () => void;
  openLoadSchema: () => void;
  openPredefinedSchema: () => void;
  showEnhancementDialog: boolean;
  toggleEnhancementDialog: () => void;
  setOpenConnection: Dispatch<SetStateAction<connectionState>>;
  showDisconnectButton: boolean;
  connectionStatus: boolean;
  combinedPatterns: string[];
  setCombinedPatterns: Dispatch<SetStateAction<string[]>>;
  combinedNodes: OptionType[];
  setCombinedNodes: Dispatch<SetStateAction<OptionType[]>>;
  combinedRels: OptionType[];
  setCombinedRels: Dispatch<SetStateAction<OptionType[]>>;
  openDataImporterSchema: () => void;
}

export interface CustomModalProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  submitLabel: string;
  submitHandler: () => void;
  statusMessage: string;
  status: 'unknown' | 'success' | 'info' | 'warning' | 'danger';
  setStatus: Dispatch<SetStateAction<'unknown' | 'success' | 'info' | 'warning' | 'danger'>>;
}

export interface CustomInput {
  value: string;
  label: string;
  placeHolder: string;
  onChangeHandler: React.ChangeEventHandler<HTMLInputElement>;
  submitHandler: (url: string) => void;
  disabledCheck: boolean;
  onCloseHandler: () => void;
  id: string;
  onBlurHandler: React.FocusEventHandler<HTMLInputElement>;
  status: 'unknown' | 'success' | 'info' | 'warning' | 'danger';
  setStatus: Dispatch<SetStateAction<'unknown' | 'success' | 'info' | 'warning' | 'danger'>>;
  statusMessage: string;
  isValid: boolean;
  isFocused: boolean;
  onPasteHandler: React.ClipboardEventHandler<HTMLInputElement>;
}

export interface CommonButtonProps {
  openModal: () => void;
  wrapperclassName?: string;
  logo: string;
  title?: string;
  className?: string;
  imgWidth?: number;
  imgeHeight?: number;
  isDisabled?: boolean;
}

export interface Source {
  page_numbers?: number[];
  source_name: string;
  start_time?: string;
}
export interface ChunkDetail {
  id: string;
  score: number;
}
export type ResponseMode = {
  message: string;
  sources?: string[];
  model?: string;
  total_tokens?: number;
  response_time?: number;
  cypher_query?: string;
  nodeDetails?: nodeDetailsProps;
  chunk_ids?: string[];
  graphonly_entities?: [];
  error?: string;
  entities?: string[];
  metric_question?: string;
  metric_contexts?: string;
  metric_answer?: string;
};
export interface Messages {
  id: number;
  user: string;
  datetime: string;
  isTyping?: boolean;
  isLoading?: boolean;
  speaking?: boolean;
  copying?: boolean;
  modes: {
    [key: string]: ResponseMode;
  };
  currentMode: string;
}

export type ChatbotProps = {
  messages: Messages[];
  setMessages: Dispatch<SetStateAction<Messages[]>>;
  isLoading: boolean;
  clear?: boolean;
  isFullScreen?: boolean;
  connectionStatus: boolean;
  isChatOnly?: boolean;
  isDeleteChatLoading: boolean;
};

export type GraphType = 'Entities' | 'DocumentChunk' | 'Communities';

export type PartialLabelNode = Partial<Node> & {
  labels: string;
};

export interface fileName {
  fileName: string;
  fileSize: number;
  url: string;
  gcsBucketName?: string;
  gcsBucketFolder?: string;
  status?: string;
  gcsProjectId: string;
  language?: string;
}
export interface URLSCAN_RESPONSE {
  status: string;
  success_count?: number;
  failed_count?: number;
  message: string;
  file_name?: fileName[];
  error?: string;
  file_source?: string;
  data?: any;
}
export interface statusAPI {
  status: string;
  message: string;
  file_name?: fileName;
}
export interface statusupdate {
  status: string;
  message: string;
  file_name: fileStatus;
}
export interface fileStatus {
  fileName: string;
  status: string;
  processingTime?: number;
  nodeCount?: number;
  relationshipCount?: number;
  model: string;
  total_chunks?: number;
  processed_chunk?: number;
  chunkNodeCount: number;
  chunkRelCount: number;
  entityNodeCount: number;
  entityEntityRelCount: number;
  communityNodeCount: number;
  communityRelCount: number;
}

export type alertStateType = {
  showAlert: boolean;
  alertType: OverridableStringUnion<AlertColor, AlertPropsColorOverrides> | undefined;
  alertMessage: string;
};
export interface BannerAlertProps extends Omit<alertStateType, 'alertType'> {
  alertType: BannerType;
}
export type Scheme = Record<string, string>;

export type LabelCount = Record<string, number>;

export interface LegendChipProps {
  scheme: Scheme;
  label: string;
  type: 'node' | 'relationship' | 'propertyKey';
  count?: number;
  onClick?: (e: React.MouseEvent<HTMLElement>) => void;
}

export interface labelsAndTypes {
  labels: string[];
  relationshipTypes: string[];
}
interface orphanTotalNodes {
  total: number;
}
export interface commonserverresponse {
  status: 'Success' | 'Failed';
  error?: string;
  message?: string | orphanTotalNodes;
  file_name?: string;
  data?:
    | OptionType
    | OptionType[]
    | string
    | string[]
    | uploadData
    | any
    | { pageitems: chunkdata[]; total_pages: number }
    | { triplets: string[] };
}

export interface chunkdata {
  text: string;
  position: number;
  pagenumber: null | number;
}

export type metricstate = {
  [key: string]: number | string;
} & {
  error: string;
};
export type metricdetails = Record<string, metricstate>;

export type multimodelmetric = {
  [key: string]: number | string;
} & {
  mode: string;
};

export interface schema {
  nodelabels: string[];
  relationshipTypes: string[];
}

export interface chatInfoMessage extends Partial<Messages> {
  sources: string[];
  model: string;
  response_time: number;
  total_tokens: number;
  mode: string;
  cypher_query?: string;
  graphonly_entities: [];
  error: string;
  entities_ids: string[];
  nodeDetails: nodeDetailsProps;
  metricquestion: string;
  metricanswer: string;
  metriccontexts: string;
  metricmodel: string;
  nodes: ExtendedNode[];
  relationships: ExtendedRelationship[];
  chunks: Chunk[];
  infoEntities: Entity[];
  communities: Community[];
  metricDetails:
    | {
        [key: string]: number | string;
      }
    | undefined;
  metricError: string;
  infoLoading: boolean;
  metricsLoading: boolean;
  activeChatmodes:
    | {
        [key: string]: ResponseMode;
      }
    | undefined;
  multiModelMetrics: multimodelmetric[];
  saveNodes: (nodes: ExtendedNode[]) => void;
  saveChunks: (chunks: Chunk[]) => void;
  saveChatRelationships: (rels: ExtendedRelationship[]) => void;
  saveCommunities: (communities: Community[]) => void;
  saveInfoEntitites: (entities: Entity[]) => void;
  saveMetrics: (metricInfo: metricstate) => void;
  toggleInfoLoading: () => void;
  toggleMetricsLoading: () => void;
  saveMultimodemetrics: (metrics: multimodelmetric[]) => void;
}

export interface eventResponsetypes extends Omit<SourceNode, 'total_chunks' | 'processingTime'> {
  total_chunks: number | null;
  processingTime: number;
}

export type Nullable<Type> = Type | null;

export type LabelColors = 'default' | 'success' | 'info' | 'warning' | 'danger' | undefined;

export interface Entity {
  element_id: string;
  labels: string[];
  properties: {
    id: string;
  };
}
export interface Community {
  id: string;
  summary: string;
  weight: number;
  level: number;
  community_rank: number;
  score?: number;
  element_id: string;
}

export interface uploadData {
  file_size: number;
  file_name: string;
  message: string;
}

export interface Chunk {
  id: string;
  position: number;
  text: string;
  fileName: string;
  length: number;
  embedding: string | null;
  page_number?: number;
  start_time?: string;
  content_offset?: string;
  url?: string;
  fileSource: string;
  score?: string;
  fileType: string;
  element_id: string;
}

export interface ExtendedNode extends Node {
  labels: string[];
  original_labels?: string[];
  properties: {
    fileName?: string;
    [key: string]: any;
  };
}

export interface ExtendedRelationship extends Relationship {
  count?: number;
}
export interface connectionState {
  openPopUp: boolean;
  chunksExists: boolean;
  vectorIndexMisMatch: boolean;
  chunksExistsWithDifferentDimension: boolean;
}
export interface Message {
  type: 'success' | 'info' | 'warning' | 'danger' | 'unknown';
  content: string | React.ReactNode;
}

export interface ChatProps {
  chatMessages: Messages[];
}

export interface filedate {
  _DateTime__date: {
    _Date__ordinal: number;
    _Date__year: number;
    _Date__month: number;
    _Date__day: number;
  };
  _DateTime__time: {
    _Time__ticks: number;
    _Time__hour: number;
    _Time__minute: number;
    _Time__second: number;
    _Time__nanosecond: number;
    _Time__tzinfo: null;
  };
}

export interface HeaderProp {
  chatOnly?: boolean;
  deleteOnClick?: () => void;
  setOpenConnection?: Dispatch<SetStateAction<connectionState>>;
  showBackButton?: boolean;
  hidePatientDropdown?: boolean;
}

export interface entity {
  id: string;
  score: number;
}

export interface community {
  id: string;
  score: number;
}

export interface nodeDetailsProps {
  chunkdetails?: ChunkDetail[];
  entitydetails?: entity[];
  communitydetails?: community[];
}
export type PatternOption = {
  label: string;
  value: string;
};

export interface duplicateNodesData {
  status?: string;
  error?: string;
  message?: any;
  data: any;
}

export interface selectedDuplicateNodes {
  firstElementId: string;
  similarElementIds: string[];
}

export interface ScehmaFromText {
  labels: string[];
  relationshipTypes: string[];
  status?: string;
  message?: string;
  data?: any;
}

export interface ScanProps {
  url?: string;
  source_type?: string;
  urlParam?: string;
  wikiquery?: string;
  model?: string;
  accessKey?: string;
  secretKey?: string;
  gcs_bucket_name?: string;
  gcs_bucket_folder?: string;
  gcs_project_id?: string;
  access_token?: string;
}

export interface ServerResponse {
  status: string;
  message: string;
  data: any;
}

export interface OrphanNodeResponse {
  status: string;
  message: any;
  total: number;
  data?: any;
  file_name?: any;
}

export interface ServerData {
  status: string;
  message: string;
  data: any;
}

export interface SourceListServerData {
  status: string;
  message: string;
  data: any;
  error?: string;
}

export interface chunksData {
  chunks: Chunk[];
  data: {
    pageitems: any[];
    total_pages: number;
  };
}

export interface ChatInfo_APIResponse {
  status: string;
  message: string;
  data: any;
}

export interface SpeechSynthesisProps {
  text?: string;
  onEnd?: () => void;
  voiceURI?: string;
  lang?: string;
  pitch?: number;
  rate?: number;
  volume?: number;
}

export interface SpeechArgs {
  text?: string;
  voiceURI?: string;
  lang?: string;
  pitch?: number;
  rate?: number;
  volume?: number;
}

export interface PollingAPI_Response {
  status: string;
  data: any;
}

export interface ContextProps {
  userCredentials: UserCredentials | null;
  setUserCredentials: React.Dispatch<React.SetStateAction<UserCredentials | null>>;
  isGdsActive: boolean;
  setGdsActive: React.Dispatch<React.SetStateAction<boolean>>;
  connectionStatus: boolean;
  setConnectionStatus: React.Dispatch<React.SetStateAction<boolean>>;
  isReadOnlyUser: boolean;
  setIsReadOnlyUser: React.Dispatch<React.SetStateAction<boolean>>;
  isBackendConnected: boolean;
  setIsBackendConnected: React.Dispatch<React.SetStateAction<boolean>>;
  errorMessage: string;
  setErrorMessage: React.Dispatch<React.SetStateAction<string>>;
  showDisconnectButton: boolean;
  setShowDisconnectButton: React.Dispatch<React.SetStateAction<boolean>>;
  isGCSActive: boolean;
  setIsGCSActive: React.Dispatch<React.SetStateAction<boolean>>;
}

export interface MessagesContextProviderProps {
  children: React.ReactNode;
}

export interface MessageContextType {
  messages: Messages[];
  setMessages: React.Dispatch<React.SetStateAction<Messages[]>>;
  clearHistoryData: boolean;
  setClearHistoryData: React.Dispatch<React.SetStateAction<boolean>>;
  isDeleteChatLoading: boolean;
  setIsDeleteChatLoading: React.Dispatch<React.SetStateAction<boolean>>;
}

export interface FileContextProviderProps {
  children: React.ReactNode;
}

export interface FileContextType {
  files: (File | null)[];
  filesData: CustomFile[];
  setFiles: React.Dispatch<React.SetStateAction<(File | null)[]>>;
  setFilesData: (value: React.SetStateAction<CustomFile[] | []>) => void;
  model: string;
  setModel: React.Dispatch<React.SetStateAction<string>>;
  graphType: string;
  setGraphType: React.Dispatch<React.SetStateAction<string>>;
  selectedRels: readonly OptionType[];
  setSelectedRels: React.Dispatch<React.SetStateAction<readonly OptionType[]>>;
  selectedNodes: readonly OptionType[];
  setSelectedNodes: React.Dispatch<React.SetStateAction<readonly OptionType[]>>;
  selectedTokenChunkSize: number;
  setSelectedTokenChunkSize: React.Dispatch<React.SetStateAction<number>>;
  selectedChunk_overlap: number;
  setSelectedChunk_overlap: React.Dispatch<React.SetStateAction<number>>;
  selectedChunks_to_combine: number;
  setSelectedChunks_to_combine: React.Dispatch<React.SetStateAction<number>>;
  rowSelection: Record<string, boolean>;
  setRowSelection: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  selectedRows: string[];
  setSelectedRows: React.Dispatch<React.SetStateAction<string[]>>;
  selectedSchemas: readonly OptionType[];
  setSelectedSchemas: React.Dispatch<React.SetStateAction<readonly OptionType[]>>;
  chatModes: string[];
  setchatModes: React.Dispatch<React.SetStateAction<string[]>>;
  setShowTextFromSchemaDialog: React.Dispatch<React.SetStateAction<showTextFromSchemaDialogType>>;
  showTextFromSchemaDialog: showTextFromSchemaDialogType;
  postProcessingTasks: string[];
  setPostProcessingTasks: React.Dispatch<React.SetStateAction<string[]>>;
  queue: any;
  setQueue: React.Dispatch<React.SetStateAction<any>>;
  processedCount: number;
  setProcessedCount: (value: React.SetStateAction<number>) => void;
  postProcessingVal: boolean;
  setPostProcessingVal: React.Dispatch<React.SetStateAction<boolean>>;
  additionalInstructions: string;
  setAdditionalInstructions: React.Dispatch<React.SetStateAction<string>>;
  schemaTextPattern: string[];
  setSchemaTextPattern: React.Dispatch<React.SetStateAction<string[]>>;
  allPatterns: string[];
  setAllPatterns: React.Dispatch<React.SetStateAction<string[]>>;
  schemaValRels: OptionType[];
  setSchemaValRels: React.Dispatch<React.SetStateAction<OptionType[]>>;
  schemaValNodes: OptionType[];
  setSchemaValNodes: React.Dispatch<React.SetStateAction<OptionType[]>>;
  schemaLoadDialog: schemaLoadDialogType;
  setSchemaLoadDialog: React.Dispatch<React.SetStateAction<schemaLoadDialogType>>;
  dbNodes: OptionType[];
  setDbNodes: React.Dispatch<React.SetStateAction<OptionType[]>>;
  dbRels: OptionType[];
  setDbRels: React.Dispatch<React.SetStateAction<OptionType[]>>;
  dbPattern: string[];
  setDbPattern: React.Dispatch<React.SetStateAction<string[]>>;
  predefinedSchemaDialog: predefinedSchemaDialogType;
  setPredefinedSchemaDialog: React.Dispatch<React.SetStateAction<predefinedSchemaDialogType>>;
  preDefinedNodes: OptionType[];
  setPreDefinedNodes: React.Dispatch<React.SetStateAction<OptionType[]>>;
  preDefinedRels: OptionType[];
  setPreDefinedRels: React.Dispatch<React.SetStateAction<OptionType[]>>;
  preDefinedPattern: string[];
  setPreDefinedPattern: React.Dispatch<React.SetStateAction<string[]>>;
  userDefinedNodes: OptionType[];
  setUserDefinedNodes: React.Dispatch<React.SetStateAction<OptionType[]>>;
  userDefinedRels: OptionType[];
  setUserDefinedRels: React.Dispatch<React.SetStateAction<OptionType[]>>;
  userDefinedPattern: string[];
  setUserDefinedPattern: React.Dispatch<React.SetStateAction<string[]>>;
  selectedPreDefOption: OptionType | null;
  setSelectedPreDefOption: React.Dispatch<React.SetStateAction<OptionType | null>>;
  sourceOptions: OptionType[];
  setSourceOptions: React.Dispatch<React.SetStateAction<OptionType[]>>;
  typeOptions: OptionType[];
  setTypeOptions: React.Dispatch<React.SetStateAction<OptionType[]>>;
  targetOptions: OptionType[];
  setTargetOptions: React.Dispatch<React.SetStateAction<OptionType[]>>;
  dataImporterSchemaDialog: dataImporterSchemaDialogType;
  setDataImporterSchemaDialog: React.Dispatch<React.SetStateAction<dataImporterSchemaDialogType>>;
  importerNodes: OptionType[];
  setImporterNodes: React.Dispatch<React.SetStateAction<OptionType[]>>;
  importerRels: OptionType[];
  setImporterRels: React.Dispatch<React.SetStateAction<OptionType[]>>;
  importerPattern: string[];
  setImporterPattern: React.Dispatch<React.SetStateAction<string[]>>;
  selectedVoice: string;
  setSelectedVoice: React.Dispatch<React.SetStateAction<string>>;
}

export interface showTextFromSchemaDialogType {
  triggeredFrom: string;
  show: boolean;
}

export interface schemaLoadDialogType {
  triggeredFrom: string;
  show: boolean;
}

export interface predefinedSchemaDialogType {
  triggeredFrom: string;
  show: boolean;
}

export interface dataImporterSchemaDialogType {
  triggeredFrom: string;
  show: boolean;
}

export interface Menuitems {
  title: string;
  onClick?: () => void;
  id?: string;
  disabledCondition?: boolean;
  isSelected?: boolean;
  selectedClassName?: string;
  description?: string;
}

export interface DatabaseStatusProps {
  status?: boolean;
  isConnected?: boolean;
  isGdsActive?: boolean;
  uri?: string;
  database?: string;
}

export interface ReusableDropdownProps {
  options: OptionType[];
  onSelect: (option: OptionType | null | void) => void;
  placeholder?: string;
  defaultValue?: string | OptionType;
  children?: React.ReactNode;
  view?: string;
  isDisabled?: boolean;
  value?: OptionType | string | null;
}

export interface HoverableLinkProps {
  url: string;
  children: React.ReactNode;
}

export interface SchemaSelectionProps {
  open: boolean;
  onClose: () => void;
  pattern?: any;
  nodes?: any;
  rels?: any;
  handleRemove?: (pattern: string) => void;
  handleSchemaView?: (view?: string) => void;
  loading?: boolean;
  highlightPattern?: string;
  onApply?: () => void;
  onCancel?: () => void;
  message?: string;
}

export type Side = 'left' | 'right' | 'top' | 'bottom';

export interface VisibilityProps {
  isVisible: boolean;
}

export interface MetricsResponse {
  status: string;
  data: any;
}

export type TupleType = any;

export interface UserDefinedGraphSchema {
  nodelabels: string[];
  relationshipTypes: string[];
  nodes: any;
  relationships: any;
  scheme: any;
}

// ─── Graph types ───
export type EntityType = 'node' | 'relationship';

export interface BasicNode {
  id: string;
  labels: string[];
  properties: Record<string, any>;
  caption?: string;
  color?: string;
  size?: number;
  html?: HTMLElement;
  selected?: boolean;
}

export interface BasicRelationship {
  id: string;
  from: string;
  to: string;
  caption?: string;
  type?: string;
  properties?: Record<string, any>;
  selected?: boolean;
}

export interface NeoNode {
  element_id: string;
  labels: string[];
  properties: Record<string, any>;
}

export interface NeoRelationship {
  element_id: string;
  start_node_element_id: string;
  end_node_element_id: string;
  type: string;
  properties?: Record<string, any>;
}

// ─── Graph Component Props ───
export interface GraphViewModalProps {
  open: boolean;
  inspectedName?: string;
  setGraphViewOpen: React.Dispatch<React.SetStateAction<boolean>>;
  viewPoint?: string;
  nodeValues?: any[];
  relationshipValues?: any[];
  selectedRows?: CustomFile[];
}

export interface SchemaViewModalProps {
  open: boolean;
  setGraphViewOpen: React.Dispatch<React.SetStateAction<boolean>>;
  viewPoint?: string;
  nodeValues?: OptionType[] | any[];
  relationshipValues?: OptionType[] | any[];
  schemaLoading?: boolean;
  view?: string;
}

export interface GraphViewButtonProps {
  nodeValues: any[];
  relationshipValues: any[];
  fill?: any;
  label?: string;
  viewType?: string;
}

export interface GraphPropertiesPanelProps {
  inspectedItem: BasicNode | BasicRelationship;
  newScheme: Scheme;
}

export interface GraphPropertiesTableProps {
  propertiesWithTypes: { key: string; value: any }[];
}

export interface CheckboxSectionProps {
  graphType: GraphType[];
  loading: boolean;
  handleChange: (type: GraphType) => void;
  isCommunity: boolean;
  isDocChunk: boolean;
  isEntity: boolean;
}

// ─── ChatBot Component Props ───
export interface ChunkProps {
  loading: boolean;
  chunks: Chunk[];
  mode: string;
}

export interface CommunitiesProps {
  loading: boolean;
  communities: Community[];
  mode: string;
}

export interface EntitiesProps {
  loading: boolean;
  mode: string;
  graphonly_entities: any[];
  infoEntities: Entity[];
}

export interface SourcesProps {
  loading: boolean;
  mode: string;
  chunks: Chunk[];
  sources: string[];
}

export interface GroupedEntity {
  texts: Set<string>;
  color: string;
}

// ─── File Table / Content Props ───
export interface FileTableProps {
  connectionStatus: boolean;
  setConnectionStatus: React.Dispatch<React.SetStateAction<boolean>>;
  onInspect: (name: string) => void;
  onRetry: (id: string) => void;
  onChunkView: (name: string) => void;
  handleGenerateGraph: () => void;
}

export interface ChildRef {
  getFiles?: () => void;
  getSelectedRows?: () => any[];
}

export interface FileTableHandle {
  getFiles: () => void;
  getSelectedRows: () => CustomFile[];
}

// ─── Popup / Dialog Props ───
export interface ConnectionModalProps {
  open: boolean;
  setOpenConnection: React.Dispatch<React.SetStateAction<connectionState>>;
  setConnectionStatus: (status: boolean) => void;
  isVectorIndexMatch?: boolean;
  chunksExistsWithoutEmbedding?: boolean;
  chunksExistsWithDifferentEmbedding?: boolean;
  onSuccess?: () => void;
  isChatOnly?: boolean;
}

export interface LargefilesProps {
  open?: boolean;
  onClose?: () => void;
  files?: CustomFile[];
  onSubmit?: () => void;
  Files?: CustomFile[];
  handleToggle?: (isChecked: boolean, id: string) => void;
  checked?: string[];
}

export interface orphanNodeProps {
  e: {
    elementId: string;
    id: string;
    labels: string[];
    properties: Record<string, any>;
  };
  documents: string[];
  chunkConnections: number;
}

export interface dupNodes {
  e: {
    elementId: string;
    id: string;
    labels: string[];
    properties: Record<string, any>;
  };
  similar: {
    elementId: string;
    id: string;
    labels: string[];
  }[];
  documents: string[];
  chunkConnections: number;
}

// ─── DrawerChatbot ───
export interface DrawerChatbotProps {
  isExpanded: boolean;
  clearHistoryData?: boolean;
  messages?: Messages[];
  connectionStatus?: boolean;
  isFullScreen?: boolean;
  toggleFullScreen?: () => void;
  closeChatBot?: () => void;
}

// ─── S3 / AWS ───
export interface S3File {
  fileName: string;
  fileSize: number;
  url: string;
}

// ─── Schema ───
export interface TupleCreationProps {
  selectedSource?: OptionType | null;
  selectedType?: OptionType | null;
  selectedTarget?: OptionType | null;
  onPatternChange: (
    source: OptionType | OptionType[] | null | undefined,
    type: OptionType | OptionType[] | null | undefined,
    target: OptionType | OptionType[] | null | undefined
  ) => void;
  onAddPattern: () => void;
  sourceOptions?: OptionType[];
  targetOptions?: OptionType[];
  typeOptions?: OptionType[];
  setSourceOptions?: React.Dispatch<React.SetStateAction<OptionType[]>>;
  setTargetOptions?: React.Dispatch<React.SetStateAction<OptionType[]>>;
  setTypeOptions?: React.Dispatch<React.SetStateAction<OptionType[]>>;
  onAdd?: (pattern: string) => void;
  selectedTupleOptions?: any[];
}

// ─── Error Types ───
export interface nonoautherror {
  message: string;
  code?: string;
  type?: string;
  [key: string]: any;
}
