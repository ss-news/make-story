import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, Search, Sparkles, Sun, Moon, Settings } from 'lucide-react'
import { useAuthUI } from '@/stores/auth'

/**
 * Top bar — ported from docs/design/story-v2/project/Web Story.html
 * (lines 167–185). Story switcher / cmdk / create / suggestions are
 * placeholders until Step 2; theme toggle and AI toggle are local UI
 * only for now.
 */
export default function Topbar() {
  const nav = useNavigate()
  const theme = useAuthUI((s) => s.theme)
  const setTheme = useAuthUI((s) => s.setTheme)
  const [aiOn, setAiOn] = useState(true)

  return (
    <div className="topbar">
      <span className="brand">
        <span className="dot" />
        Web Story
      </span>

      <div
        className="switcher"
        onClick={() => nav('/dashboard')}
        role="button"
        tabIndex={0}
      >
        <span style={{ fontFamily: 'var(--font-serif)', fontSize: 13, fontStyle: 'italic' }}>
          Lý Thanh Vân
        </span>
        <span className="meta">— chưa chọn truyện</span>
        <ChevronDown size={11} />
      </div>

      <button type="button" className="top-action" disabled>
        <Search size={11} /> Tìm
        <span className="kbd" style={{ marginLeft: 6 }}>⌘K</span>
      </button>

      <button
        type="button"
        className="top-action"
        style={{ color: 'var(--accent)', borderColor: 'var(--accent)' }}
        disabled
      >
        + Tạo
        <span className="kbd" style={{ marginLeft: 6 }}>⌘N</span>
      </button>

      <button type="button" className="top-action" disabled>
        <Sparkles size={11} /> Gợi ý AI
      </button>

      <div className="topbar-spacer" />

      <button
        type="button"
        className={`ai-toggle ${aiOn ? 'on' : 'off'}`}
        onClick={() => setAiOn((v) => !v)}
        aria-pressed={aiOn}
      >
        <span className="pulse" /> AI {aiOn ? 'ON' : 'OFF'}
      </button>

      <button
        type="button"
        className="top-action"
        onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
        aria-label="Toggle theme"
      >
        {theme === 'light' ? <Moon size={12} /> : <Sun size={12} />}
      </button>

      <button type="button" className="top-action" aria-label="Cài đặt" disabled>
        <Settings size={12} />
      </button>
    </div>
  )
}
