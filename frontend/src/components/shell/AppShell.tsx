import { Outlet } from 'react-router-dom'

// Placeholder shell — replaced with the pixel-perfect implementation in Task 1.12.
export default function AppShell() {
  return (
    <div className="min-h-screen bg-paper">
      <Outlet />
    </div>
  )
}
