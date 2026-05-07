import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, ApiError } from './client'

export type User = {
  id: string
  email: string
  display_name: string
  is_admin: boolean
  ai_enabled: boolean
}

export const meQueryKey = ['auth', 'me'] as const

export function useMe() {
  return useQuery({
    queryKey: meQueryKey,
    queryFn: () => apiFetch<User>('/api/auth/me'),
    retry: (count, err) => !(err instanceof ApiError && err.status === 401) && count < 1,
  })
}

export function useRegister() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: { email: string; password: string; display_name: string }) =>
      apiFetch<User>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: (user) => qc.setQueryData(meQueryKey, user),
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: { email: string; password: string }) =>
      apiFetch<User>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: (user) => qc.setQueryData(meQueryKey, user),
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<{ status: string }>('/api/auth/logout', { method: 'POST' }),
    onSuccess: () => qc.setQueryData(meQueryKey, null),
  })
}
