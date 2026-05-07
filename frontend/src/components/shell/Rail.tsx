import { map } from 'lodash-es'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  Home,
  FileText,
  Map,
  Users,
  Network,
  Calendar,
  Globe,
  Settings,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

/**
 * Left rail — ported from docs/design/story-v2/project/Web Story.html
 * (lines 187–200). 7 nav buttons + theme/divider + settings.
 *
 * Step 1: only `dashboard` and `settings` are routable. Story-scoped
 * buttons render disabled visually until a story is selected (Step 2).
 */

type RailItem = {
  id: string
  icon: LucideIcon
  label: string
  to?: string // when undefined, button is disabled (no story selected yet)
}

const RAIL_ITEMS: RailItem[] = [
  { id: 'dashboard', icon: Home, label: 'Dự án', to: '/dashboard' },
  { id: 'editor', icon: FileText, label: 'Editor' },
  { id: 'storymap', icon: Map, label: 'Story Map' },
  { id: 'characters', icon: Users, label: 'Nhân vật' },
  { id: 'rels', icon: Network, label: 'Quan hệ' },
  { id: 'events', icon: Calendar, label: 'Events' },
  { id: 'world', icon: Globe, label: 'World Bible' },
]

export default function Rail() {
  const { pathname } = useLocation()
  const nav = useNavigate()

  return (
    <div className="rail">
      {map(RAIL_ITEMS, (r) => {
        const Icon = r.icon
        const disabled = !r.to
        const active = r.to ? pathname === r.to || pathname.startsWith(r.to + '/') : false
        return (
          <button
            key={r.id}
            type="button"
            className={`ricon${active ? ' active' : ''}${disabled ? ' disabled' : ''}`}
            onClick={() => r.to && nav(r.to)}
            disabled={disabled}
            title={r.label}
          >
            <Icon size={16} />
            <span className="rail-label">{r.label}</span>
          </button>
        )
      })}

      <div style={{ flex: 1 }} />
      <div className="divider" />

      <NavLink
        to="/settings"
        title="Cài đặt"
        className={({ isActive }) => `ricon disabled${isActive ? ' active' : ''}`}
        // Settings page is Step 2 — render disabled visual but keep markup parity.
        onClick={(e) => e.preventDefault()}
      >
        <Settings size={16} />
        <span className="rail-label">Cài đặt</span>
      </NavLink>
    </div>
  )
}
