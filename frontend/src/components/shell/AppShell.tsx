import { Outlet } from 'react-router-dom'
import Topbar from './Topbar'
import Rail from './Rail'
import Statusbar from './Statusbar'
import './shell.css'

/**
 * Authed app shell.
 *
 * Layout mirrors docs/design/story-v2/project/Web Story.html (lines 165–237):
 *   - 40px topbar across both columns
 *   - 56px rail in the left column
 *   - main outlet in the right column
 *   - 22px statusbar across both columns
 *
 * The grid styles live in `shell.css` under the `.app` class so that
 * structure stays in lockstep with the design source.
 */
export default function AppShell() {
  return (
    <div className="app">
      <Topbar />
      <Rail />
      <main className="main overflow-auto">
        <Outlet />
      </main>
      <Statusbar />
    </div>
  )
}
