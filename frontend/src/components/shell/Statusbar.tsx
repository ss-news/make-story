import { useMe } from '@/api/auth'

/**
 * Bottom status bar — adapted from
 * docs/design/story-v2/project/Web Story.html (lines 224–233).
 *
 * Spec §5.5 adaptation: replace the original "SQLite local · path"
 * indicator with the current user's email. Web build is multi-user, so
 * we surface the logged-in identity in place of the local-DB label.
 */
export default function Statusbar() {
  const { data: user } = useMe()
  return (
    <div className="statusbar">
      <span className="sb-item">
        <span className="k">DỰ ÁN</span>
        <span className="text-ink">—</span>
      </span>
      <span className="sb-item">
        <span className="k">CH</span> 0/0
      </span>
      <span className="sb-item">
        <span className="k">TỪ</span> 0
      </span>
      <span className="sb-item">
        <span className="k">ARC</span> —
      </span>

      <span className="sb-spacer" />

      {user && (
        <span className="sb-item">
          <span className="k">Đăng nhập:</span>
          <span className="text-ink">{truncate(user.email, 28)}</span>
        </span>
      )}
      <span className="sb-item" style={{ color: 'var(--ok)' }}>
        ● Đã lưu
      </span>
      <span className="sb-item">v0.1</span>
    </div>
  )
}

function truncate(s: string, n: number) {
  return s.length <= n ? s : s.slice(0, n - 1) + '…'
}
