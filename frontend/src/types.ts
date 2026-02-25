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
  email: string;
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
