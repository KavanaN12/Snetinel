import {
  AxiosError,
  AxiosHeaders,
  type AxiosAdapter,
  type InternalAxiosRequestConfig,
} from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import apiClient from '../src/api/client';

function makeResponse(
  config: InternalAxiosRequestConfig,
  status: number,
  data: Record<string, string>,
) {
  return {
    config,
    data,
    headers: new AxiosHeaders(),
    status,
    statusText: status === 200 ? 'OK' : 'Unauthorized',
  };
}

function rejectUnauthorized(config: InternalAxiosRequestConfig) {
  return Promise.reject(
    new AxiosError(
      'Unauthorized',
      AxiosError.ERR_BAD_REQUEST,
      config,
      undefined,
      makeResponse(config, 401, { detail: 'Expired token' }),
    ),
  );
}

describe('API authentication refresh', () => {
  let storage: Map<string, string>;
  let redirect: ReturnType<typeof vi.fn>;
  let calls: string[];

  beforeEach(() => {
    storage = new Map();
    redirect = vi.fn();
    calls = [];
    vi.stubGlobal('window', {
      localStorage: {
        getItem: (key: string) => storage.get(key) ?? null,
        removeItem: (key: string) => storage.delete(key),
        setItem: (key: string, value: string) => storage.set(key, value),
      },
      location: { assign: redirect, pathname: '/dashboard' },
    });
  });

  afterEach(() => {
    apiClient.defaults.adapter = undefined;
    vi.unstubAllGlobals();
  });

  it('refreshes an expired access token and retries the original request once', async () => {
    storage.set(
      'sentinel-auth',
      JSON.stringify({
        state: { accessToken: 'expired-access', refreshToken: 'valid-refresh' },
      }),
    );
    const adapter: AxiosAdapter = async (config) => {
      calls.push(config.url ?? '');
      if (config.url === '/auth/refresh') {
        return makeResponse(config, 200, {
          access_token: 'fresh-access',
          refresh_token: 'rotated-refresh',
        });
      }
      if (config.headers.Authorization !== 'Bearer fresh-access') {
        return rejectUnauthorized(config);
      }
      return makeResponse(config, 200, { ok: 'true' });
    };
    apiClient.defaults.adapter = adapter;

    const response = await apiClient.get('/private');

    expect(response.data).toEqual({ ok: 'true' });
    expect(calls).toEqual(['/private', '/auth/refresh', '/private']);
    expect(JSON.parse(storage.get('sentinel-auth') ?? '{}').state).toMatchObject({
      accessToken: 'fresh-access',
      refreshToken: 'rotated-refresh',
    });
    expect(redirect).not.toHaveBeenCalled();
  });

  it('clears expired authentication without recursively refreshing the refresh endpoint', async () => {
    storage.set(
      'sentinel-auth',
      JSON.stringify({
        state: { accessToken: 'expired-access', refreshToken: 'expired-refresh' },
      }),
    );
    apiClient.defaults.adapter = async (config) => {
      calls.push(config.url ?? '');
      return rejectUnauthorized(config);
    };

    await expect(apiClient.get('/private')).rejects.toMatchObject({
      response: { status: 401 },
    });

    expect(calls).toEqual(['/private', '/auth/refresh']);
    expect(storage.has('sentinel-auth')).toBe(false);
    expect(redirect).toHaveBeenCalledWith('/login');
  });
});
