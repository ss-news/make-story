import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'light' | 'dark'

type AuthUI = {
  theme: Theme
  setTheme: (t: Theme) => void
}

/**
 * UI-only store for theme and other persisted preferences.
 *
 * Auth status itself comes from the TanStack Query `useMe()` hook — this
 * store deliberately does NOT mirror auth state.
 */
export const useAuthUI = create<AuthUI>()(
  persist(
    (set) => ({
      theme: 'light',
      setTheme: (theme) => {
        if (typeof document !== 'undefined') {
          document.body.dataset.theme = theme
        }
        set({ theme })
      },
    }),
    { name: 'make-story-ui' },
  ),
)
