import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { url } from '../utils/Utils';

// When the backend requires a signed-in user on every route (public deployments), each
// request to it must carry the login token. Several calls use fetch or plain axios rather
// than the shared API client, and the shared client only adds the token after the
// connection is set up, so requests made right after a page refresh went out without it.
// This attaches the token to every request bound for the backend, whatever made it.

const TOKEN_KEY = 'aushadha_auth_token';

const backendBase = () => url().replace(/\/+$/, '');

const isBackendUrl = (target: string | undefined): boolean => {
  if (!target) {
    return false;
  }
  const base = backendBase();
  return Boolean(base) && target.startsWith(base);
};

const token = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
};

const addToAxios = (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
  const t = token();
  // A relative url on an instance with a baseURL (the shared API client) goes to the baseURL
  const target = config.baseURL && !/^[a-z]+:\/\//i.test(config.url ?? '') ? config.baseURL : config.url;
  if (t && isBackendUrl(target) && !config.headers.has('Authorization')) {
    config.headers.set('Authorization', `Bearer ${t}`);
  }
  return config;
};

export const attachTokenToAxios = (instance: AxiosInstance) => {
  instance.interceptors.request.use(addToAxios);
};

let installed = false;

export const installAuthTokenForBackendRequests = () => {
  if (installed) {
    return;
  }
  installed = true;

  attachTokenToAxios(axios);

  const originalFetch = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const target = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    const t = token();
    if (!t || !isBackendUrl(target)) {
      return originalFetch(input, init);
    }
    const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
    if (!headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${t}`);
    }
    return originalFetch(input, { ...init, headers });
  };
};
