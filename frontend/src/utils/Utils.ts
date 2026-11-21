import { calcWordColor } from '@neo4j-devtools/word-color';
import type { Relationship } from '@neo4j-nvl/base';
import {
  CustomFile,
  Entity,
  ExtendedNode,
  ExtendedRelationship,
  filedate,
  GraphType,
  Messages,
  Scheme,
  SourceNode,
  UserCredentials,
  OptionType,
  UserDefinedGraphSchema,
  TupleType,
} from '../types';
import Wikipediadarkmode from '../assets/images/wikipedia-darkmode.svg';
import Wikipediadlogo from '../assets/images/wikipedia.svg';
import webdarklogo from '../assets/images/web-darkmode.svg';
import weblogo from '../assets/images/web.svg';
import youtubedarklogo from '../assets/images/youtube-darkmode.svg';
import youtubelightlogo from '../assets/images/youtube-lightmode.svg';
import s3logo from '../assets/images/s3logo.png';
import gcslogo from '../assets/images/gcs.webp';
import { chatModeLables, EXPIRATION_DAYS } from './Constants';

// Get the Url
export const url = () => {
  let url = window.location.href.replace('5173', '8000');
  if (import.meta.env.VITE_BACKEND_API_URL) {
    url = import.meta.env.VITE_BACKEND_API_URL;
  }
  return !url || !url.match('/$') ? url : url.substring(0, url.length - 1);
};

// validation check for s3 bucket url
export const validation = (url: string) => {
  return url.trim() != '' && /^s3:\/\/([^/]+)\/?$/.test(url) != false;
};

export const wikiValidation = (url: string) => {
  return url.trim() != '' && /https:\/\/([a-zA-Z]{2,3})\.wikipedia\.org\/wiki\/(.*)/gm.test(url) != false;
};
export const webLinkValidation = (url: string) => {
  return (
    url.trim() != '' &&
    /(http(s)?:\/\/.)?(www\.)?[-a-zA-Z0-9@:%._~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_.~#?&//=]*)/g.test(url) != false
  );
};
export const youtubeLinkValidation = (url: string) => {
  return (
    url.trim() != '' &&
    /^(?:https?:\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$/.test(
      url
    ) != false
  );
};
// Status indicator icons to status column
export const statusCheck = (status: string) => {
  switch (status) {
    case 'New':
      return 'info';
    case 'N/A':
      return 'unknown';
    case 'Completed':
      return 'success';
    case 'Processing':
      return 'warning';
    case 'Uploading':
      return 'warning';
    case 'Failed':
      return 'danger';
    case 'Upload Failed':
      return 'danger';
    case 'Ready to Reprocess':
      return 'info';
    default:
      return 'unknown';
  }
};

// Graph Functions
export const constructQuery = (queryTochange: string, docLimit: string) => {
  return `MATCH docs = (d:Document {status:'Completed'}) 
  WITH docs, d ORDER BY d.createdAt DESC 
  LIMIT ${docLimit}
  CALL { WITH d
    OPTIONAL MATCH chunks=(d)<-[:PART_OF]-(c:Chunk)
    RETURN chunks, c LIMIT 50
  }
  WITH [] 
  ${queryTochange}
  AS paths
  CALL { WITH paths UNWIND paths AS path UNWIND nodes(path) as node RETURN collect(distinct node) as nodes }
  CALL { WITH paths UNWIND paths AS path UNWIND relationships(path) as rel RETURN collect(distinct rel) as rels }
  RETURN nodes, rels`;
};

export const constructDocQuery = (queryTochange: string) => {
  return `
MATCH docs = (d:Document {status:'Completed'}) 
WHERE d.fileName = $document_name
WITH docs, d ORDER BY d.createdAt DESC 
CALL { WITH d
  OPTIONAL MATCH chunks=(d)<-[:PART_OF]-(c:Chunk)
  RETURN chunks, c LIMIT 50
}
WITH [] 
${queryTochange}
AS paths
CALL { WITH paths UNWIND paths AS path UNWIND nodes(path) as node RETURN collect(distinct node) as nodes }
CALL { WITH paths UNWIND paths AS path UNWIND relationships(path) as rel RETURN collect(distinct rel) as rels }
RETURN nodes, rels`;
};

export const nodeHasLabel = (node: any, label: string) => {
  const labelsToCheck = node.original_labels || node.labels || [];
  return labelsToCheck.includes(label);
};

export const getSize = (node: any) => {
  if (nodeHasLabel(node, 'Document')) {
    return 40;
  }
  if (nodeHasLabel(node, 'Chunk')) {
    return 30;
  }
  return 30;
};

export const getNodeCaption = (node: any) => {
  if (node.properties.name) {
    return node.properties.name;
  }
  if (node.properties.text) {
    return node.properties.text;
  }
  if (node.properties.fileName) {
    return node.properties.fileName;
  }
  if (nodeHasLabel(node, '__Community__')) {
    return node.properties.title;
  }
  return node.properties.id;
};

export const getIcon = (node: any) => {
  if (nodeHasLabel(node, 'Document')) {
    return 'paginate-filter-text.svg';
  }
  if (nodeHasLabel(node, 'Chunk')) {
    return 'paragraph-left-align.svg';
  }
  return undefined;
};
export function extractPdfFileName(url: string): string {
  const splitUrl = url.split('/');
  const [encodedFileName] = splitUrl[splitUrl.length - 1].split('?');
  const decodedFileName = decodeURIComponent(encodedFileName);
  if (decodedFileName.includes('/')) {
    const splitedstr = decodedFileName.split('/');
    return splitedstr[splitedstr.length - 1];
  }
  return decodedFileName;
}

// Caption inside a node circle. A block of n lines may be as wide as the circle's chord
// at the block's top and bottom edge (2·√(r² − (h/2)²)), so one line can span most of the
// circle while three lines stay narrower, and no corner crosses the edge. The largest font
// (and fewest lines) at which whole words fit is chosen, measured with the label's own
// font; if nothing fits, the smallest font is used, long words break, and anything after
// the last line is cut with an ellipsis.
const LABEL_MAX_LINES = 3;
const LABEL_LINE_HEIGHT = 1.25; // room for Indic scripts' vowel signs above and below
const LABEL_EDGE_GAP = 3; // px kept clear of the circle's edge
const LABEL_FONT =
  "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";
let labelMeasureCtx: CanvasRenderingContext2D | null = null;

// Lines the words take when wrapped at word boundaries in `width`; Infinity if a word is wider than a line
const wrappedLineCount = (words: string[], fontSize: number, width: number): number => {
  if (!labelMeasureCtx) {
    labelMeasureCtx = document.createElement('canvas').getContext('2d');
  }
  const ctx = labelMeasureCtx;
  if (!ctx) {
    return 1;
  }
  ctx.font = `${fontSize}px ${LABEL_FONT}`;
  const space = ctx.measureText(' ').width;
  let lines = 1;
  let used = 0;
  for (const word of words) {
    const w = ctx.measureText(word).width;
    if (w > width) {
      return Infinity;
    }
    if (used === 0) {
      used = w;
    } else if (used + space + w <= width) {
      used += space + w;
    } else {
      lines += 1;
      used = w;
    }
  }
  return lines;
};

// Widest text block of `lines` lines that fits inside a circle of radius r (0 if none)
const chordWidth = (r: number, lines: number, fontSize: number): number => {
  const half = (lines * fontSize * LABEL_LINE_HEIGHT) / 2;
  return half >= r ? 0 : Math.floor(2 * Math.sqrt(r * r - half * half));
};

export function createHtmlLabel(caption: string, nodeSize: number = 40): HTMLElement {
  const diameter = nodeSize * 2;
  const r = nodeSize - LABEL_EDGE_GAP;
  const text = (caption ?? '').replace(/\s+/g, ' ').trim();
  const words = text ? text.split(' ') : [];

  const base = Math.max(9, Math.round(nodeSize * 0.28));
  const minFont = 7;
  let fontSize = minFont;
  let maxLines = 1;
  let width = chordWidth(r, 1, minFont);
  let fitted = false;
  for (let size = base; size >= minFont && !fitted; size--) {
    for (let lines = 1; lines <= LABEL_MAX_LINES; lines++) {
      const w = chordWidth(r, lines, size);
      if (w > 0 && wrappedLineCount(words, size, w) <= lines) {
        fontSize = size;
        maxLines = lines;
        width = w;
        fitted = true;
        break;
      }
    }
  }
  if (!fitted) {
    // Smallest font, as many lines as fit; long words break and the rest is cut
    for (let lines = LABEL_MAX_LINES; lines >= 1; lines--) {
      const w = chordWidth(r, lines, minFont);
      if (w > 0) {
        maxLines = lines;
        width = w;
        break;
      }
    }
  }

  // Outer element fills the node and centres the text box
  const htmlEl = document.createElement('div');
  htmlEl.style.width = `${diameter}px`;
  htmlEl.style.height = `${diameter}px`;
  htmlEl.style.display = 'flex';
  htmlEl.style.alignItems = 'center';
  htmlEl.style.justifyContent = 'center';
  htmlEl.style.pointerEvents = 'none';
  htmlEl.style.backgroundColor = 'transparent';

  const textEl = document.createElement('div');
  textEl.innerText = text;
  textEl.style.maxWidth = `${width}px`;
  textEl.style.color = '#000000';
  textEl.style.fontSize = `${fontSize}px`;
  textEl.style.lineHeight = `${LABEL_LINE_HEIGHT}`;
  // Generic sans-serif stack supporting all OS-native typographic ligatures
  textEl.style.fontFamily = LABEL_FONT;
  textEl.style.textAlign = 'center';
  // Break inside a word only when the word alone is wider than the box
  textEl.style.overflowWrap = 'anywhere';
  textEl.style.wordBreak = 'break-word';
  textEl.style.overflow = 'hidden';
  textEl.style.textOverflow = 'ellipsis';
  // Cut to maxLines with an ellipsis
  textEl.style.display = '-webkit-box';
  textEl.style.setProperty('-webkit-box-orient', 'vertical');
  textEl.style.setProperty('-webkit-line-clamp', String(maxLines));
  textEl.style.setProperty('line-clamp', String(maxLines));

  htmlEl.appendChild(textEl);
  return htmlEl;
}

// Graph text longer than this is content (e.g. a chunk's text), not a label: not translated
const MAX_GRAPH_TOKEN = 200;

export async function translateGraphTokens(texts: string[], lang: string): Promise<Record<string, string>> {
  const identity = Object.fromEntries(texts.map((t) => [t, t]));
  const tokens = texts.filter((t) => t && t.length <= MAX_GRAPH_TOKEN);
  if (lang === 'en' || tokens.length === 0) {
    return identity;
  }
  try {
    // Known terms come from the backend's translation cache; new ones are translated once and cached
    const res = await fetch(`${url()}/translate/dynamic/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texts: tokens, lang }),
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const data = await res.json();
    return { ...identity, ...(data?.translations ?? {}) };
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('[translateGraphTokens] failed', e);
    return identity;
  }
}

export const processGraphData = (
  neoNodes: ExtendedNode[],
  neoRels: ExtendedRelationship[],
  tokenTranslations?: Record<string, string>
) => {
  const schemeVal: Scheme = {};
  let iterator = 0;
  const filteredNeoNodes = neoNodes.filter((node: any) => {
    // Original (English) labels: the backend may have translated node.labels
    const labels = node.original_labels || node.labels || [];
    return !labels.includes('*') && !labels.includes('__Entity__');
  });

  const labels: string[] = filteredNeoNodes.flatMap((f: any) => f.labels);
  for (let index = 0; index < labels.length; index++) {
    const label = labels[index];
    if (schemeVal[label] == undefined) {
      schemeVal[label] = calcWordColor(label);
      iterator += 1;
    }
  }
  const newNodes: ExtendedNode[] = filteredNeoNodes.map((g: any) => {
    const rawCaption = getNodeCaption(g);
    const translatedCaption = tokenTranslations?.[rawCaption] || rawCaption;
    const nodeSize = getSize(g);
    return {
      id: g.element_id,
      size: nodeSize,
      captionAlign: 'bottom',
      iconAlign: 'bottom',
      caption: '',
      html: createHtmlLabel(translatedCaption, nodeSize),
      color: schemeVal[g.labels[0]],
      icon: getIcon(g),
      labels: g.labels,
      original_labels: g.original_labels,
      properties: g.properties,
    };
  });
  const finalNodes = newNodes.flat();
  const validNodeIds = new Set(finalNodes.map((node) => node.id));
  const newRels: Relationship[] = neoRels
    .filter(
      (relations: any) =>
        validNodeIds.has(relations.start_node_element_id) && validNodeIds.has(relations.end_node_element_id)
    )
    .map((relations: any) => {
      return {
        id: relations.element_id,
        from: relations.start_node_element_id,
        to: relations.end_node_element_id,
        caption: tokenTranslations?.[relations.type] || relations.type,
      };
    });
  const finalRels = newRels.flat();
  return { finalNodes, finalRels, schemeVal };
};

/**
 * Filters nodes, relationships, and scheme based on the selected graph types.
 *
 * @param graphType - An array of graph types to filter by (e.g., 'DocumentChunk', 'Entities', 'Communities').
 * @param allNodes - An array of all nodes present in the graph.
 * @param allRelationships - An array of all relationships in the graph.
 * @param scheme - The scheme object containing node and relationship information.
 * @returns An object containing filtered nodes, relationships, and scheme based on the selected graph types.
 */
export const filterData = (
  graphType: GraphType[],
  allNodes: ExtendedNode[],
  allRelationships: Relationship[],
  scheme: Scheme
) => {
  let filteredNodes: ExtendedNode[] = [];
  let filteredRelations: Relationship[] = [];
  let filteredScheme: Scheme = {};
  const entityTypes = Object.keys(scheme).filter(
    (type) => type !== 'Document' && type !== 'Chunk' && type !== '__Community__'
  );
  // Only Document + Chunk
  // const processedEntities = entityTypes.flatMap(item => item.includes(',') ? item.split(',') : item);
  if (graphType.includes('DocumentChunk') && !graphType.includes('Entities') && !graphType.includes('Communities')) {
    filteredNodes = allNodes.filter(
      (node) => (nodeHasLabel(node, 'Document') && node.properties.fileName) || nodeHasLabel(node, 'Chunk')
    );
    const nodeIds = new Set(filteredNodes.map((node) => node.id));
    filteredRelations = allRelationships.filter(
      (rel) =>
        ['PART_OF', 'FIRST_CHUNK', 'SIMILAR', 'NEXT_CHUNK'].includes(rel.caption ?? '') &&
        nodeIds.has(rel.from) &&
        nodeIds.has(rel.to)
    );
    filteredScheme = { Document: scheme.Document, Chunk: scheme.Chunk };
    // Only Entity
  } else if (
    graphType.includes('Entities') &&
    !graphType.includes('DocumentChunk') &&
    !graphType.includes('Communities')
  ) {
    const entityNodes = allNodes.filter(
      (node) => !nodeHasLabel(node, 'Document') && !nodeHasLabel(node, 'Chunk') && !nodeHasLabel(node, '__Community__')
    );
    filteredNodes = entityNodes ? entityNodes : [];
    const nodeIds = new Set(filteredNodes.map((node) => node.id));
    filteredRelations = allRelationships.filter(
      (rel) =>
        !['PART_OF', 'FIRST_CHUNK', 'HAS_ENTITY', 'SIMILAR', 'NEXT_CHUNK'].includes(rel.caption ?? '') &&
        nodeIds.has(rel.from) &&
        nodeIds.has(rel.to)
    );
    filteredScheme = Object.fromEntries(entityTypes.map((key) => [key, scheme[key]])) as Scheme;
    // Only Communities
  } else if (
    graphType.includes('Communities') &&
    !graphType.includes('DocumentChunk') &&
    !graphType.includes('Entities')
  ) {
    filteredNodes = allNodes.filter((node) => nodeHasLabel(node, '__Community__'));
    const nodeIds = new Set(filteredNodes.map((node) => node.id));
    filteredRelations = allRelationships.filter(
      (rel) =>
        ['IN_COMMUNITY', 'PARENT_COMMUNITY'].includes(rel.caption ?? '') && nodeIds.has(rel.from) && nodeIds.has(rel.to)
    );
    filteredScheme = { __Community__: scheme.__Community__ };
    // Document + Chunk + Entity
  } else if (
    graphType.includes('DocumentChunk') &&
    graphType.includes('Entities') &&
    !graphType.includes('Communities')
  ) {
    filteredNodes = allNodes.filter(
      (node) =>
        (nodeHasLabel(node, 'Document') && node.properties.fileName) ||
        nodeHasLabel(node, 'Chunk') ||
        (!nodeHasLabel(node, 'Document') && !nodeHasLabel(node, 'Chunk') && !nodeHasLabel(node, '__Community__'))
    );
    const nodeIds = new Set(filteredNodes.map((node) => node.id));
    filteredRelations = allRelationships.filter(
      (rel) =>
        !['IN_COMMUNITY', 'PARENT_COMMUNITY'].includes(rel.caption ?? '') &&
        nodeIds.has(rel.from) &&
        nodeIds.has(rel.to)
    );
    filteredScheme = {
      Document: scheme.Document,
      Chunk: scheme.Chunk,
      ...Object.fromEntries(entityTypes.map((key) => [key, scheme[key]])),
    };
    // Entities + Communities
  } else if (
    graphType.includes('Entities') &&
    graphType.includes('Communities') &&
    !graphType.includes('DocumentChunk')
  ) {
    const entityNodes = allNodes.filter((node) => !nodeHasLabel(node, 'Document') && !nodeHasLabel(node, 'Chunk'));
    const communityNodes = allNodes.filter((node) => nodeHasLabel(node, '__Community__'));
    filteredNodes = [...entityNodes, ...communityNodes];
    const nodeIds = new Set(filteredNodes.map((node) => node.id));
    filteredRelations = allRelationships.filter(
      (rel) =>
        !['PART_OF', 'FIRST_CHUNK', 'SIMILAR', 'NEXT_CHUNK'].includes(rel.caption ?? '') &&
        nodeIds.has(rel.from) &&
        nodeIds.has(rel.to)
    );
    filteredScheme = {
      ...Object.fromEntries(entityTypes.map((key) => [key, scheme[key]])),
      __Community__: scheme.__Community__,
    };
    // Document + Chunk + Communities
  } else if (
    graphType.includes('DocumentChunk') &&
    graphType.includes('Communities') &&
    !graphType.includes('Entities')
  ) {
    const documentChunkNodes = allNodes.filter(
      (node) => (nodeHasLabel(node, 'Document') && node.properties.fileName) || nodeHasLabel(node, 'Chunk')
    );
    const communityNodes = allNodes.filter((node) => nodeHasLabel(node, '__Community__'));
    filteredNodes = [...documentChunkNodes, ...communityNodes];
    const nodeIds = new Set(filteredNodes.map((node) => node.id));
    filteredRelations = allRelationships.filter(
      (rel) =>
        ['PART_OF', 'FIRST_CHUNK', 'SIMILAR', 'NEXT_CHUNK', 'IN_COMMUNITY', 'PARENT_COMMUNITY'].includes(
          rel.caption ?? ''
        ) &&
        nodeIds.has(rel.from) &&
        nodeIds.has(rel.to)
    );
    filteredScheme = { Document: scheme.Document, Chunk: scheme.Chunk, __Community__: scheme.__Community__ };
    // Document + Chunk + Entity + Communities (All types)
  } else if (
    graphType.includes('DocumentChunk') &&
    graphType.includes('Entities') &&
    graphType.includes('Communities')
  ) {
    filteredNodes = allNodes;
    filteredRelations = allRelationships;
    filteredScheme = scheme;
  }
  return { filteredNodes, filteredRelations, filteredScheme };
};
export const getDateTime = () => {
  const date = new Date();
  const formattedDateTime = `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
  return formattedDateTime;
};

export const getIsLoading = (messages: Messages[]) => {
  return messages.some((msg) => msg.isTyping || msg.isLoading);
};
export const calculateProcessingTime = (fileSizeBytes: number, processingTimePerByteSeconds: number) => {
  const totalProcessingTimeSeconds = (fileSizeBytes / 1000) * processingTimePerByteSeconds;
  const minutes = Math.floor(totalProcessingTimeSeconds / 60);
  const seconds = Math.floor(totalProcessingTimeSeconds % 60);
  return { minutes, seconds };
};

export const capitalize = (word: string): string => {
  return `${word[0].toUpperCase()}${word.slice(1)}`;
};
export const parseEntity = (entity: Entity) => {
  const { labels, properties } = entity;
  let [label] = labels;
  const text = properties.id;
  if (!label) {
    label = 'Entity';
  }
  return { label, text };
};

export const titleCheck = (title: string) => {
  return title === 'Chunk' || title === 'Document';
};

export const getFileSourceStatus = (item: SourceNode) => {
  if (item?.fileSource === 's3 bucket' && localStorage.getItem('accesskey') === item?.awsAccessKeyId) {
    return item?.status;
  }
  if (item?.fileSource === 'local file') {
    return item?.status;
  }
  if (item?.status === 'Completed' || item.status === 'Failed' || item.status === 'Ready to Reprocess') {
    return item?.status;
  }
  if (
    item?.fileSource === 'Wikipedia' ||
    item?.fileSource === 'youtube' ||
    item?.fileSource === 'gcs bucket' ||
    item?.fileSource === 'web-url'
  ) {
    return item?.status;
  }
  return 'N/A';
};
export const isFileCompleted = (waitingFile: CustomFile, item: SourceNode) =>
  waitingFile && item.status === 'Completed';

export const calculateProcessedCount = (prev: number, batchSize: number) =>
  (prev === batchSize ? batchSize - 1 : prev + 1);

export const isProcessingFileValid = (item: SourceNode, userCredentials: UserCredentials) => {
  return item.status === 'Processing' && item.fileName != undefined && userCredentials && userCredentials.database;
};
export const sortAlphabetically = (a: Relationship, b: Relationship) => {
  const captionOne = a.caption?.toLowerCase() || '';
  const captionTwo = b.caption?.toLowerCase() || '';
  return captionOne.localeCompare(captionTwo);
};

export const capitalizeWithPlus = (s: string) => {
  return s
    .split('+')
    .map((s) => capitalize(s))
    .join('+');
};
export const capitalizeWithUnderscore = (s: string) => capitalize(s).split('_').join(' ');

export const getDescriptionForChatMode = (mode: string): string => {
  switch (mode.toLowerCase()) {
    case chatModeLables.vector:
      return 'Utilizes vector indexing on text chunks to enable semantic similarity search.';
    case chatModeLables.graph:
      return 'Leverages text-to-cypher translation to query a database and retrieve relevant data, ensuring a highly targeted and contextually accurate response.';
    case chatModeLables['graph+vector']:
      return 'Combines vector indexing on text chunks with graph connections, enhancing search results with contextual relevance by considering relationships between concepts.';
    case chatModeLables.fulltext:
      return 'Employs a fulltext index on text chunks for rapid keyword-based search, efficiently identifying documents containing specific words or phrases.';
    case chatModeLables['graph+vector+fulltext']:
      return 'Merges vector indexing, graph connections, and fulltext indexing for a comprehensive search approach, combining semantic similarity, contextual relevance, and keyword-based search for optimal results.';
    case chatModeLables['entity search+vector']:
      return 'Combines entity node vector indexing with graph connections for accurate entity-based search, providing the most relevant response.';
    case chatModeLables['global search+vector+fulltext']:
      return 'Use vector and full-text indexing on community nodes to provide accurate, context-aware answers globally.';
    default:
      return 'Chat mode description not available'; // Fallback description
  }
};
export const getLogo = (mode: string): Record<string, string> => {
  if (mode === 'light') {
    return {
      Wikipedia: Wikipediadarkmode,
      'web-url': webdarklogo,
      's3 bucket': s3logo,
      youtube: youtubedarklogo,
      'gcs bucket': gcslogo,
    };
  }
  return {
    Wikipedia: Wikipediadlogo,
    'web-url': weblogo,
    's3 bucket': s3logo,
    youtube: youtubelightlogo,
    'gcs bucket': gcslogo,
  };
};

export const generateYouTubeLink = (url: string, startTime: string) => {
  try {
    const urlObj = new URL(url);
    urlObj.searchParams.set('t', startTime);
    return urlObj.toString();
  } catch (error) {
    console.error('Invalid URL:', error);
    return '';
  }
};
export function isAllowedHost(url: string, allowedHosts: string[]) {
  try {
    const parsedUrl = new URL(url);
    return allowedHosts.includes(parsedUrl.host);
  } catch (e) {
    return false;
  }
}

export const getCheckboxConditions = (allNodes: ExtendedNode[]) => {
  const isDocChunk = allNodes.some((n) => nodeHasLabel(n, 'Document') || nodeHasLabel(n, 'Chunk'));
  const isEntity = allNodes.some(
    (n) => !nodeHasLabel(n, 'Document') && !nodeHasLabel(n, 'Chunk') && !nodeHasLabel(n, '__Community__')
  );
  const isCommunity = allNodes.some((n) => nodeHasLabel(n, '__Community__'));
  return { isDocChunk, isEntity, isCommunity };
};

export const graphTypeFromNodes = (allNodes: ExtendedNode[]) => {
  const graphType: GraphType[] = [];
  const hasDocChunk = allNodes.some((n) => nodeHasLabel(n, 'Document') || nodeHasLabel(n, 'Chunk'));
  const hasEntity = allNodes.some(
    (n) => !nodeHasLabel(n, 'Document') && !nodeHasLabel(n, 'Chunk') && !nodeHasLabel(n, '__Community__')
  );
  const hasCommunity = allNodes.some((n) => nodeHasLabel(n, '__Community__'));
  if (hasDocChunk) {
    graphType.push('DocumentChunk');
  }
  if (hasEntity) {
    graphType.push('Entities');
  }
  if (hasCommunity) {
    graphType.push('Communities');
  }
  return graphType;
};
export function downloadClickHandler<Type>(
  JsonData: Type,
  downloadLinkRef: React.RefObject<HTMLAnchorElement>,
  filename: string
) {
  const textFile = new Blob([JSON.stringify(JsonData)], { type: 'application/json' });
  if (downloadLinkRef && downloadLinkRef.current) {
    downloadLinkRef.current.href = URL.createObjectURL(textFile);
    downloadLinkRef.current.download = filename;
    downloadLinkRef.current.click();
  }
}
export function getNodes<Type extends Entity | ExtendedNode>(nodesData: Array<Type>, mode: string) {
  return nodesData.map((n) => {
    if (!n.labels.length && mode === chatModeLables['entity search+vector']) {
      return {
        ...n,
        labels: ['Entity'],
      };
    }
    return n;
  });
}
export function getParsedDate(neo4jdate: filedate) {
  const { _Date__year, _Date__month, _Date__day } = neo4jdate._DateTime__date;
  const { _Time__hour, _Time__minute, _Time__second } = neo4jdate._DateTime__time;
  const currentdate = new Date(`${_Date__month}/${_Date__day}/${_Date__year}`);
  currentdate.setHours(_Time__hour, _Time__minute, _Time__second);
  return currentdate;
}

export function isExpired(itemdate: Date) {
  const currentDate = new Date();
  const timedifference = currentDate.getTime() - itemdate.getTime();
  const daysdifference = timedifference / (1000 * 3600 * 24);
  return daysdifference > EXPIRATION_DAYS;
}

export function isFileReadyToProcess(file: CustomFile, withLocalCheck: boolean) {
  if (withLocalCheck) {
    return file.fileSource === 'local file' && file.status === 'New';
  }
  return file.status === 'New' || file.status == 'Ready to Reprocess';
}

export const updateLocalStorage = (userCredentials: UserCredentials, key: string, data: any, patientEmail?: string) => {
  const fullKey = patientEmail ? `${patientEmail}_${key}` : key;
  localStorage.setItem(fullKey, JSON.stringify({ db: userCredentials?.uri, selectedOptions: data }));
};

export const userDefinedGraphSchema = (nodes: OptionType[], relationships: OptionType[]): UserDefinedGraphSchema => {
  const schemeVal: Scheme = {};
  let iterator = 0;
  const transformedNodes: ExtendedNode[] = nodes.map((node, index) => {
    const { label } = node;
    if (schemeVal[label] === undefined) {
      schemeVal[label] = calcWordColor(label);
      iterator += 1;
    }
    const nodeSize = 40;
    return {
      id: `node-${index + 0}`,
      element_id: `node-${index + 0}`,
      size: nodeSize,
      color: schemeVal[label],
      caption: '',
      html: createHtmlLabel(label, nodeSize),
      labels: [label],
      properties: {
        name: label,
        indexes: label === 'Chunk' ? ['text', 'embedding'] : [],
        constraints: [],
      },
    };
  });

  const nodeMap: Record<string, string> = transformedNodes.reduce(
    (acc, node) => {
      acc[node.labels[0]] = node.id;
      return acc;
    },
    {} as Record<string, string>
  );
  const transformedRelationships: ExtendedRelationship[] = relationships
    .map((rel, index) => {
      const parts = rel.value.split(',');
      if (parts.length !== 3) {
        console.warn(`Invalid relationship format: ${rel}`);
        return null;
      }
      const [start, type, end] = parts.map((part) => part.trim());
      if (!nodeMap[start] || !nodeMap[end]) {
        console.warn(`Missing node(s) for relationship: ${start} -[:${type}]-> ${end}`);
        return null;
      }
      return {
        id: `rel-${index + 100}`,
        element_id: `rel-${index + 100}`,
        from: nodeMap[start],
        to: nodeMap[end],
        caption: type,
        type,
        properties: {
          name: type,
        },
      };
    })
    .filter((rel) => rel !== null) as ExtendedRelationship[];
  return {
    nodes: transformedNodes,
    relationships: transformedRelationships,
    scheme: schemeVal,
  } as any;
};

export const getSelectedTriplets = (
  selectedOptions: OptionType[] | OptionType
): {
  value: string;
  label: string;
  source: string;
  target: string;
  type: string;
}[] => {
  const selectedArray = Array.isArray(selectedOptions) ? selectedOptions : [selectedOptions];
  const triplets = [];
  for (const option of selectedArray) {
    let tripletArray: string[];
    try {
      tripletArray = JSON.parse(option.value);
    } catch (error) {
      console.error('Error parsing selected option value:', option.value, error);
      continue;
    }
    if (!Array.isArray(tripletArray)) {
      continue;
    }
    for (const tripletString of tripletArray) {
      const matchResult = tripletString.match(/(.*?)-([A-Z_]+)->(.*)/);
      if (!matchResult) {
        continue;
      }
      const [source, rel, target] = matchResult.slice(1).map((s: any) => s.trim());
      triplets.push({
        value: `${source},${rel},${target}`,
        label: `${source} -[:${rel}]-> ${target}`,
        source,
        target,
        type: rel,
      });
    }
  }
  return triplets;
};

export const extractOptions = (schemaTuples: TupleType[]) => {
  const nodeLabelSet = new Set<string>();
  const relationshipSet = new Set<string>();
  schemaTuples.forEach((tuple: any) => {
    if (tuple.source) {
      nodeLabelSet.add(tuple.source);
    }
    if (tuple.target) {
      nodeLabelSet.add(tuple.target);
    }
    if (tuple.value || tuple.type) {
      relationshipSet.add(tuple.value || tuple.type);
    }
  });
  const nodeLabelOptions: OptionType[] = Array.from(nodeLabelSet).map((label) => ({
    label,
    value: label,
  }));

  const relationshipTypeOptions: OptionType[] = Array.from(relationshipSet).map((relValue) => ({
    label: relValue,
    value: relValue,
  }));
  return { nodeLabelOptions, relationshipTypeOptions };
};

type RawNode = {
  id: string;
  labels: string[];
  properties: Record<string, any>;
};
type RawRelationship = {
  id: string;
  caption: string;
  from: string;
  to: string;
};

export const extractGraphSchemaFromRawData = (
  nodes: RawNode[],
  relationships: RawRelationship[]
): {
  nodes: OptionType[];
  relationships: OptionType[];
} => {
  const uniqueLabels = new Set<string>();
  const nodeList: OptionType[] = [];
  for (const node of nodes) {
    for (const label of node.labels) {
      if (!uniqueLabels.has(label)) {
        uniqueLabels.add(label);
        nodeList.push({ label, value: label });
      }
    }
  }
  const relList: OptionType[] = [];
  for (const rel of relationships) {
    const startNodes = nodes.filter((n) => n.id === rel.from);
    const endNodes = nodes.filter((n) => n.id === rel.to);
    const relType = rel.caption;
    for (const startNode of startNodes) {
      for (const endNode of endNodes) {
        const startLabel = startNode.labels[0];
        const endLabel = endNode.labels[0];
        relList.push({
          label: `${startLabel} -[:${relType}]-> ${endLabel}`,
          value: `${startLabel}, ${relType}, ${endLabel}`,
        });
      }
    }
  }
  return {
    nodes: nodeList,
    relationships: relList,
  };
};

export const generateGraphFromNodeAndRelVals = (
  nodeVals: OptionType[],
  relVals: OptionType[]
): UserDefinedGraphSchema => {
  const schemeVal: Scheme = {};
  const uniqueNodesMap = new Map<string, ExtendedNode>();
  let nodeIdCounter = 0;
  nodeVals.forEach((node) => {
    const key = `${node.label}-${node.value}`;
    if (!uniqueNodesMap.has(key)) {
      if (!schemeVal[node.label]) {
        schemeVal[node.label] = calcWordColor(node.label);
      }
      uniqueNodesMap.set(key, {
        id: `node-${nodeIdCounter}`,
        size: 40,
        color: schemeVal[node.label],
        caption: '',
        html: createHtmlLabel(node.label, 40),
        labels: [node.label],
        properties: {
          name: node.value,
          indexes: node.label === 'Chunk' ? ['text', 'embedding'] : [],
          constraints: [],
        },
      });
      nodeIdCounter++;
    }
  });
  const transformedNodes = Array.from(uniqueNodesMap.values());
  const nodeValueToIdMap: Record<string, string> = {};
  transformedNodes.forEach((node) => {
    // @ts-ignore
    nodeValueToIdMap[node.labels[0]] = node.id;
  });
  const seenRelTypes = new Set<string>();
  const transformedRelationships: ExtendedRelationship[] = [];
  relVals.forEach((rel) => {
    const parts = rel.value.split(',');
    if (parts.length !== 3) {
      console.warn(`Invalid relationship format: ${rel.value}`);
      return;
    }
    const [start, type, end] = parts.map((part) => part.trim());
    if (seenRelTypes.has(type)) {
      return;
    }
    seenRelTypes.add(type);
    const fromId = nodeValueToIdMap[start];
    const toId = nodeValueToIdMap[end];
    if (!fromId || !toId) {
      console.warn(`Missing node(s) for relationship: ${start} -[:${type}]-> ${end}`);
      return;
    }
    transformedRelationships.push({
      id: `rel-${transformedRelationships.length + 100}`,
      from: fromId,
      to: toId,
      caption: type,
      type,
    });
  });
  return {
    nodelabels: transformedNodes.map((n) => n.properties.name as string),
    relationshipTypes: transformedRelationships.map((r) => r.type as string),
    scheme: schemeVal,
  } as any;
};
export function parseRelationshipString(input: string): {
  value: string;
  label: string;
  source: string;
  target: string;
  type: string;
} {
  const regex = /(\w+)\s+-\[:([\w_]+)]->\s+(\w+)/;
  const match = input.match(regex);

  if (!match) {
    throw new Error(`Invalid relationship format: ${input}`);
  }

  const [_, source, type, target] = match;

  return {
    value: `${source},${type},${target}`,
    label: input,
    source,
    target,
    type,
  };
}

interface UpdateOptionsParams {
  patterns: { label: string; value: string }[];
  currentSourceOptions: OptionType[];
  currentTargetOptions: OptionType[];
  currentTypeOptions: OptionType[];
  setSourceOptions: React.Dispatch<React.SetStateAction<OptionType[]>>;
  setTargetOptions: React.Dispatch<React.SetStateAction<OptionType[]>>;
  setTypeOptions: React.Dispatch<React.SetStateAction<OptionType[]>>;
}

export const updateSourceTargetTypeOptions = async ({
  patterns,
  currentSourceOptions,
  currentTargetOptions,
  currentTypeOptions,
  setSourceOptions,
  setTargetOptions,
  setTypeOptions,
}: UpdateOptionsParams) => {
  const newNodesSet = new Set<string>();
  const newRelsSet = new Set<string>();
  patterns.forEach(({ value }) => {
    const match = value.match(/^(.+?) -\[:(.+?)\]-> (.+)$/);
    if (match) {
      const [, source, rel, target] = match.map((s) => s.trim());
      newNodesSet.add(source);
      newNodesSet.add(target);
      newRelsSet.add(rel);
    }
  });

  const appendNewValues = (current: OptionType[], newVal: Set<string>): OptionType[] => {
    const existingLabels = new Set(current.map((item) => item.label));
    const newItems: OptionType[] = [];
    newVal.forEach((label) => {
      if (!existingLabels.has(label)) {
        newItems.push({ label, value: label });
      }
    });
    return [...current, ...newItems];
  };
  const newSourceOptions = appendNewValues(currentSourceOptions, newNodesSet);
  const newTargetOptions = appendNewValues(currentTargetOptions, newNodesSet);
  const newTypeOptions = appendNewValues(currentTypeOptions, newRelsSet);
  setSourceOptions(newSourceOptions);
  setTargetOptions(newTargetOptions);
  setTypeOptions(newTypeOptions);
  return [newSourceOptions, newTargetOptions, newTypeOptions];
};

export const deduplicateNodeByValue = (arrays: { value: any }[]) => {
  const map = new Map();
  arrays.forEach((item: { value: any }) => {
    if (!map.has(item.value)) {
      map.set(item.value, item);
    }
  });
  return Array.from(map.values());
};

export const deduplicateByFullPattern = (arrays: { value: string; label: string }[]) => {
  const seen = new Set<string>();
  const result: { value: string; label: string }[] = [];
  arrays.forEach((item) => {
    if (!seen.has(item.value)) {
      seen.add(item.value);
      result.push(item);
    }
  });
  return result;
};

export const importerValidation = (url: string) => {
  return url.trim() !== '' && /^https:\/\/console-preview\.neo4j\.io\/tools\/import\/models(\/.*)?$/i.test(url);
};

export const isNeo4jUser = (email?: string): boolean => {
  if (!email) {
    return false;
  }
  return email.toLowerCase().endsWith('@neo4j.com');
};

export const shouldShowTokenTracking = (email?: string): boolean => {
  return !isNeo4jUser(email);
};
