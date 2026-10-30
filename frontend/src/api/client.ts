import axios, {
  AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios';

const fallbackBaseURL = '/api/v1';
const normalizeBaseURL = (value: string) => value.replace(/\/+$/, '');
const baseURL = normalizeBaseURL(import.meta.env.VITE_API_BASE_URL || fallbackBaseURL);
const storageKey = 'sentinel-auth';

const apiClient = axios.create({
  baseURL,
  withCredentials: true,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
});

type StoredTokenState = {
  state?: {
    accessToken?: string;
    refreshToken?: string;
  };
};

type RetriableRequestConfig = InternalAxiosRequestConfig & { _retriedAfterRefresh?: boolean };
type TokenResponse = { access_token: string; refresh_token: string };

let refreshPromise: Promise<TokenResponse> | null = null;
let loginRedirectStarted = false;

function getStoredTokens() {
  if (typeof window === 'undefined') return { accessToken: null as string | null, refreshToken: null as string | null };
  const raw = window.localStorage.getItem(storageKey);
  if (!raw) return { accessToken: null, refreshToken: null };
  try {
    const parsed = JSON.parse(raw) as StoredTokenState;
    return {
      accessToken: parsed.state?.accessToken ?? null,
      refreshToken: parsed.state?.refreshToken ?? null,
    };
  } catch {
    return { accessToken: null, refreshToken: null };
  }
}

function clearStoredSession() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(storageKey);
  if (!loginRedirectStarted && window.location.pathname !== '/login') {
    loginRedirectStarted = true;
    window.location.assign('/login');
  }
}

function persistTokens(tokens: TokenResponse, fallbackRefreshToken: string) {
  if (typeof window === 'undefined') return;
  const raw = window.localStorage.getItem(storageKey);
  if (!raw) throw new Error('Stored authentication state is missing during token refresh.');
  const parsed = JSON.parse(raw) as StoredTokenState;
  parsed.state = {
    ...parsed.state,
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token || fallbackRefreshToken,
  };
  window.localStorage.setItem(storageKey, JSON.stringify(parsed));
}

function refreshTokens(refreshToken: string): Promise<TokenResponse> {
  if (!refreshPromise) {
    refreshPromise = apiClient
      .post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken })
      .then(({ data }) => {
        persistTokens(data, refreshToken);
        return data;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

apiClient.interceptors.request.use((config) => {
  const { accessToken } = getStoredTokens();
  if (accessToken && config.headers) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail.map((item) => (typeof item === 'string' ? item : item.msg ?? 'Request failed')).join(', ');
    }
    if (error.message) {
      return error.message;
    }
  }
  return error instanceof Error ? error.message : 'Request failed';
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: string }>) => {
    const status = error.response?.status;
    const originalRequest = error.config as RetriableRequestConfig | undefined;
    if (status !== 401 || !originalRequest) return Promise.reject(error);

    const requestUrl = originalRequest.url ?? '';
    if (requestUrl.endsWith('/auth/refresh')) {
      clearStoredSession();
      return Promise.reject(error);
    }
    if (requestUrl.endsWith('/auth/login') || requestUrl.endsWith('/auth/register')) {
      return Promise.reject(error);
    }
    if (originalRequest._retriedAfterRefresh) {
      clearStoredSession();
      return Promise.reject(error);
    }

    const { refreshToken } = getStoredTokens();
    if (!refreshToken) {
      clearStoredSession();
      return Promise.reject(error);
    }

    originalRequest._retriedAfterRefresh = true;
    try {
      const tokens = await refreshTokens(refreshToken);
      originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      clearStoredSession();
      return Promise.reject(refreshError);
    }
  },
);

export default apiClient;
