import type { Config } from 'tailwindcss'
import animate from 'tailwindcss-animate'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        // Design tokens (from tokens.css)
        paper: 'var(--paper)',
        'paper-2': 'var(--paper-2)',
        'paper-3': 'var(--paper-3)',
        ink: 'var(--ink)',
        'ink-2': 'var(--ink-2)',
        muted: 'var(--muted)',
        'muted-2': 'var(--muted-2)',
        hairline: 'var(--hairline)',
        'hairline-strong': 'var(--hairline-strong)',
        accent: 'var(--accent)',
        'accent-soft': 'var(--accent-soft)',
        warn: 'var(--warn)',
        ok: 'var(--ok)',
        turning: 'var(--turning)',

        // shadcn aliases mapped to design tokens (tokens are color values, no hsl() wrapper needed)
        background: 'var(--paper)',
        foreground: 'var(--ink)',
        card: 'var(--paper-2)',
        'card-foreground': 'var(--ink)',
        popover: 'var(--paper-2)',
        'popover-foreground': 'var(--ink)',
        primary: 'var(--accent)',
        'primary-foreground': 'var(--paper)',
        secondary: 'var(--paper-3)',
        'secondary-foreground': 'var(--ink)',
        'muted-foreground': 'var(--muted)',
        'accent-foreground': 'var(--ink)',
        destructive: 'var(--warn)',
        'destructive-foreground': 'var(--paper)',
        border: 'var(--hairline)',
        input: 'var(--hairline)',
        ring: 'var(--accent)',
      },
      fontFamily: {
        mono: 'var(--font-mono)',
        serif: 'var(--font-serif)',
        sans: 'var(--font-sans)',
      },
      borderRadius: {
        lg: 'var(--radius, 0.5rem)',
        md: 'calc(var(--radius, 0.5rem) - 2px)',
        sm: 'calc(var(--radius, 0.5rem) - 4px)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [animate],
} satisfies Config
