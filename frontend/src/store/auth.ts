import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserResponse } from '../types/api';

const STORAGE_KEY = 'sentinel-auth';

interface AuthState {
  user: UserResponse | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  setAuth: (args: { user: UserResponse; accessToken: string; refreshToken: string }) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      setAuth: ({ user, accessToken, refreshToken }) =>
        set({ user, accessToken, refreshToken, isAuthenticated: true }),
      logout: () => set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false }),
    }),
    {
      name: STORAGE_KEY,
      partialize: (state) => ({ user: state.user, accessToken: state.accessToken, refreshToken: state.refreshToken, isAuthenticated: state.isAuthenticated }),
      onRehydrateStorage: () => (state) => {
        if (state && typeof window !== 'undefined') {
          const persisted = window.localStorage.getItem(STORAGE_KEY);
          if (persisted) {
            try {
              const parsed = JSON.parse(persisted) as { state?: { accessToken?: string | null } };
              if (!parsed.state?.accessToken) {
                state.logout();
              }
            } catch {
              state?.logout();
            }
          }
        }
      },
    },
  ),
);
