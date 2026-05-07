import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

describe('tokens.css', () => {
  const tokens = fs.readFileSync(path.resolve(__dirname, 'tokens.css'), 'utf-8')

  it('declares all required light-theme tokens', () => {
    const required = [
      '--paper', '--paper-2', '--paper-3',
      '--ink', '--ink-2', '--muted', '--muted-2',
      '--hairline', '--hairline-strong',
      '--accent', '--accent-soft',
      '--font-mono', '--font-serif', '--font-sans',
    ]
    for (const t of required) {
      expect(tokens).toContain(t)
    }
  })

  it('declares dark theme override', () => {
    expect(tokens).toMatch(/\[data-theme="dark"\]/)
  })
})
