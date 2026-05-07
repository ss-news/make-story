import { Navigate, Outlet } from 'react-router-dom'
import { useMe } from '@/api/auth'

export default function ProtectedRoute() {
  const { data, isLoading, isError } = useMe()
  if (isLoading) return <div className="p-4 text-muted">…</div>
  if (isError || !data) return <Navigate to="/login" replace />
  return <Outlet />
}
