import { useMemo } from 'react';

const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');

const resolveApiBase = () => {
  const configured = import.meta.env.VITE_API_BASE_URL;
  if (configured) {
    if (typeof window !== 'undefined') {
      try {
        const url = new URL(configured, window.location.origin);
        const hostname = url.hostname.toLowerCase();
        const isContainerAlias =
          !hostname.includes('.') &&
          hostname !== 'localhost' &&
          hostname !== '127.0.0.1' &&
          hostname !== '0.0.0.0';
        if (isContainerAlias) {
          url.hostname = window.location.hostname || 'localhost';
        }
        return trimTrailingSlash(url.toString());
      } catch {
        return trimTrailingSlash(configured);
      }
    }
    return trimTrailingSlash(configured);
  }
  if (typeof window !== 'undefined') {
    const url = new URL(window.location.href);
    const port = url.port === '5173' ? '8000' : url.port || '8000';
    return trimTrailingSlash(`${url.protocol}//${url.hostname}:${port}`);
  }
  return trimTrailingSlash('http://localhost:8000');
};

const API_BASE = resolveApiBase();
const ADMIN_TOKEN = import.meta.env.VITE_ADMIN_TOKEN;

type RequestInitWithBody = RequestInit & { body?: BodyInit; json?: unknown };

const useApi = () => {
  const client = useMemo(() => {
    const request = async <T>(path: string, init: RequestInitWithBody = {}): Promise<T> => {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...init.headers
      };
      if (ADMIN_TOKEN) {
        headers['X-API-KEY'] = ADMIN_TOKEN;
      }

      let body = init.body;
      if (init.json !== undefined) {
        body = JSON.stringify(init.json);
      }

      const response = await fetch(`${API_BASE}${path}`, { ...init, headers, body });
      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        throw new Error(errorBody.detail || response.statusText);
      }
      if (response.status === 204) {
        return {} as T;
      }
      return response.json() as Promise<T>;
    };

    return {
      get: <T>(path: string) => request<T>(path),
      post: <T>(path: string, json: unknown) => request<T>(path, { method: 'POST', json }),
      del: <T>(path: string) => request<T>(path, { method: 'DELETE' })
    };
  }, []);

  return client;
};

export default useApi;
