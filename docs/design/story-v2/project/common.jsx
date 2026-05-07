// Common helpers + small components shared across screens

const { useState, useEffect, useMemo, useRef, useCallback } = React;

function classNames(...xs) { return xs.filter(Boolean).join(' '); }

function initials(name) {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 1).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function Avatar({ name, size = 'md', color, square = false }) {
  return (
    <span
      className={classNames('avatar', size === 'lg' && 'lg', size === 'xs' && 'xs', square && 'sq')}
      style={color ? { borderColor: color, color: color, background: 'transparent' } : null}
      title={name}
    >{initials(name)}</span>
  );
}

function Tag({ children, color, solid }) {
  return (
    <span className={classNames('tag', solid && 'solid')} style={color ? { borderColor: color, color: color } : null}>{children}</span>
  );
}

// Icon helpers — minimal line icons using inline SVG paths
function Icon({ name, size = 14 }) {
  const paths = {
    edit: <path d="M3 13l1-4 8-8 3 3-8 8-4 1zM10 3l3 3" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>,
    map: <><path d="M2 4l4-1 4 1 4-1v10l-4 1-4-1-4 1V4z" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinejoin="round"/><path d="M6 3v11M10 4v11" stroke="currentColor" strokeWidth="1.2" fill="none"/></>,
    users: <><circle cx="6" cy="6" r="2.4" stroke="currentColor" strokeWidth="1.2" fill="none"/><circle cx="11.5" cy="6.5" r="2" stroke="currentColor" strokeWidth="1.2" fill="none"/><path d="M2 13c0-2 2-3.5 4-3.5s4 1.5 4 3.5M9 13c0-1.5 1.5-2.8 3-2.8s2 1.3 2 2.8" stroke="currentColor" strokeWidth="1.2" fill="none"/></>,
    graph: <><circle cx="3" cy="8" r="1.6" stroke="currentColor" strokeWidth="1.2" fill="var(--paper)"/><circle cx="13" cy="3" r="1.6" stroke="currentColor" strokeWidth="1.2" fill="var(--paper)"/><circle cx="13" cy="13" r="1.6" stroke="currentColor" strokeWidth="1.2" fill="var(--paper)"/><circle cx="8" cy="8" r="1.6" stroke="currentColor" strokeWidth="1.2" fill="var(--paper)"/><path d="M4.5 8H6.5M9.5 8H11.5M9 7l3-3M9 9l3 3" stroke="currentColor" strokeWidth="1"/></>,
    bolt: <path d="M9 1L3 9h4l-1 6 6-8h-4l1-6z" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinejoin="round"/>,
    book: <><path d="M2 3h5c1 0 1 1 1 1v10s0-1-1-1H2V3zM14 3H9c-1 0-1 1-1 1v10s0-1 1-1h5V3z" stroke="currentColor" strokeWidth="1.2" fill="none"/></>,
    home: <path d="M2 8L8 3l6 5v6H10v-4H6v4H2V8z" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinejoin="round"/>,
    settings: <><circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.2" fill="none"/><path d="M8 1.5v2M8 12.5v2M14.5 8h-2M3.5 8h-2M12.6 3.4l-1.4 1.4M4.8 11.2l-1.4 1.4M12.6 12.6l-1.4-1.4M4.8 4.8L3.4 3.4" stroke="currentColor" strokeWidth="1.2"/></>,
    search: <><circle cx="7" cy="7" r="4" stroke="currentColor" strokeWidth="1.2" fill="none"/><path d="M10 10l4 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></>,
    sun: <><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.2" fill="none"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M2.8 2.8l1.4 1.4M11.8 11.8l1.4 1.4M13.2 2.8l-1.4 1.4M4.2 11.8l-1.4 1.4" stroke="currentColor" strokeWidth="1.2"/></>,
    moon: <path d="M13 9.5A5 5 0 016.5 3a5 5 0 105 6.5z" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinejoin="round"/>,
    plus: <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>,
    x: <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>,
    chevron: <path d="M5 4l4 4-4 4" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>,
    chevronDown: <path d="M4 5l4 4 4-4" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>,
    sparkle: <path d="M8 2l1.4 4.2L13.5 7.5L9.4 8.9L8 13L6.6 8.9L2.5 7.5L6.6 6.2L8 2zM13 11l.6 1.6L15 13l-1.4.6L13 15l-.6-1.4L11 13l1.4-.4L13 11z" fill="currentColor"/>,
    save: <><path d="M3 3h8l2 2v8H3V3z" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinejoin="round"/><path d="M5 3v4h6V3M5 13v-3h6v3" stroke="currentColor" strokeWidth="1.2" fill="none"/></>,
    diamond: <path d="M8 2l5 5-5 7-5-7 5-5z" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinejoin="round"/>,
    star: <path d="M8 2l1.6 4 4.4.4-3.4 2.8 1.2 4.4L8 11.4 4.2 13.6 5.4 9.2 2 6.4l4.4-.4L8 2z" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinejoin="round"/>,
    list: <path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>,
    bold: <path d="M4 3h4a2.5 2.5 0 010 5H4V3zM4 8h5a2.5 2.5 0 010 5H4V8z" stroke="currentColor" strokeWidth="1.2" fill="none"/>,
    italic: <path d="M6 3h6M4 13h6M9 3l-2 10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>,
    h1: <text x="2" y="12" fontSize="11" fontFamily="serif" fontWeight="600" fill="currentColor">H1</text>,
    h2: <text x="2" y="12" fontSize="11" fontFamily="serif" fontWeight="600" fill="currentColor">H2</text>,
    quote: <path d="M3 6c0-1.5 1-3 3-3v2c-1 0-1.5.5-1.5 1.5V8H6v4H3V6zM10 6c0-1.5 1-3 3-3v2c-1 0-1.5.5-1.5 1.5V8H13v4h-3V6z" fill="currentColor"/>,
    drag: <><circle cx="6" cy="4" r="1" fill="currentColor"/><circle cx="10" cy="4" r="1" fill="currentColor"/><circle cx="6" cy="8" r="1" fill="currentColor"/><circle cx="10" cy="8" r="1" fill="currentColor"/><circle cx="6" cy="12" r="1" fill="currentColor"/><circle cx="10" cy="12" r="1" fill="currentColor"/></>,
    eye: <><path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z" stroke="currentColor" strokeWidth="1.2" fill="none"/><circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.2" fill="none"/></>,
    filter: <path d="M2 3h12l-4 6v4l-4-1V9L2 3z" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinejoin="round"/>,
    arrow: <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" style={{ display: 'inline-block', verticalAlign: 'middle' }}>
      {paths[name] || null}
    </svg>
  );
}

// Toggle switch
function Toggle({ on, onChange, label }) {
  return (
    <button className={classNames('toggle', on && 'on')} onClick={() => onChange(!on)}>
      <span className="sw"/>
      {label && <span style={{ fontSize: 11 }}>{label}</span>}
    </button>
  );
}

// Storyline accent helper
function getStorylineColor(slId) {
  const sl = window.SEED.storylines.find(s => s.id === slId);
  return sl ? sl.color : 'var(--accent)';
}
function getStoryline(slId) {
  return window.SEED.storylines.find(s => s.id === slId);
}
function getCharacter(cid) {
  return window.SEED.characters.find(c => c.id === cid);
}
function getArc(aid) {
  return window.SEED.arcs.find(a => a.id === aid);
}
function getChapter(chId) {
  return window.SEED.chapters.find(c => c.id === chId);
}
function getEvent(eid) {
  return window.SEED.events.find(e => e.id === eid);
}

Object.assign(window, { classNames, initials, Avatar, Tag, Icon, Toggle, getStorylineColor, getStoryline, getCharacter, getArc, getChapter, getEvent });
