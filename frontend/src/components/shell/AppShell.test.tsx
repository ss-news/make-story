import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi } from 'vitest'

vi.mock('@/api/auth', () => ({
  useMe: () => ({
    data: {
      id: '1',
      email: 'alice@example.com',
      display_name: 'Alice',
      is_admin: false,
      ai_enabled: false,
    },
    isLoading: false,
    isError: false,
  }),
  useLogout: () => ({ mutate: vi.fn(), isPending: false }),
}))

import AppShell from './AppShell'

describe('AppShell', () => {
  it('renders topbar, rail, statusbar with login email', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <AppShell />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByText(/alice@example.com/)).toBeInTheDocument()
    expect(screen.getByText(/Web Story/i)).toBeInTheDocument()
  })
})
