import axios, { type AxiosError } from 'axios';

const fallbackBaseURL = '/api/v1';
const normalizeBaseURL = (value: string) => value.replace(/\/+$/, '');
const baseURL = normalizeBaseURL(import.meta.env.VITE_API_BASE_URL || fallbackBaseURL);

const apiClient = axios.create({
  baseURL,
  withCredentials: true,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
});

function getStoredTokens() {
  if (typeof window === 'undefined') return { accessToken: null as string | null, refreshToken: null as string | null };
  const raw = window.localStorage.getItem('sentinel-auth');
  if (!raw) return { accessToken: null, refreshToken: null };
  try {
    const parsed = JSON.parse(raw) as { state?: { accessToken?: string; refreshToken?: string } };
    return {
      accessToken: parsed.state?.accessToken ?? null,
      refreshToken: parsed.state?.refreshToken ?? null,
    };
  } catch {
    return { accessToken: null, refreshToken: null };
  }
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
    if (status === 401) {
      const { refreshToken } = getStoredTokens();
      if (refreshToken) {
        try {
          const response = await apiClient.post('/auth/refresh', { refresh_token: refreshToken });
          const nextToken = response.data as { access_token?: string; refresh_token?: string };
          if (nextToken.access_token && typeof window !== 'undefined') {
            const raw = window.localStorage.getItem('sentinel-auth');
            if (raw) {
              const parsed = JSON.parse(raw) as { state?: Record<string, unknown> };
              parsed.state = {
                ...parsed.state,
                accessToken: nextToken.access_token,
                refreshToken: nextToken.refresh_token ?? refreshToken,
              };
              window.localStorage.setItem('sentinel-auth', JSON.stringify(parsed));
            }
            const originalRequest = error.config;
            if (originalRequest) {
              originalRequest.headers.Authorization = `Bearer ${nextToken.access_token}`;
              return apiClient(originalRequest);
            }
          }
        } catch {
          // fall through to logout
        }
      }
          if (typeof window !== 'undefined') {
        window.localStorage.removeItem('sentinel-auth');
        window.location.assign('/login');
      }
    }
    return Promise.reject(error);
  },
);

export default apiClient;
