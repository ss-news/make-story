// Automatic Muse sign-in for accounts that log in with email + one-time code.
// The code is read from the user's own inbox web page (OTP domain): its URL is a template
// with {email}, {user} and {domain}, opened in a hidden window with its own saved session
// so the user can sign in to the inbox site once ("Open inbox site").
const { BrowserWindow } = require('electron');

const INBOX_PARTITION = 'persist:otp-inbox';
const CODE_TIMEOUT_MS = 150000;
const POLL_MS = 5000;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function inboxUrl(template, email) {
  const [user, domain = ''] = String(email).split('@');
  return String(template)
    .replaceAll('{email}', encodeURIComponent(email))
    .replaceAll('{user}', encodeURIComponent(user))
    .replaceAll('{domain}', encodeURIComponent(domain));
}

// Codes near words a Meta/Muse login mail uses come first; any 4–8 digit number is the fallback.
function findCodes(text) {
  const near = [], other = [];
  const words = /code|otp|verif|confirm|meta|muse|login|log in|sign in|mã|xác/i;
  for (const line of String(text).split(/\n+/)) {
    for (const match of line.matchAll(/(?<![\d#])(\d{4,8})(?!\d)/g)) {
      (words.test(line) ? near : other).push(match[1]);
    }
  }
  return [...new Set([...near, ...other])];
}

let inboxWindow = null;
function getInboxWindow() {
  if (inboxWindow && !inboxWindow.isDestroyed()) return inboxWindow;
  inboxWindow = new BrowserWindow({
    width: 1000, height: 760, show: false, title: 'OTP inbox',
    webPreferences: { partition: INBOX_PARTITION, contextIsolation: true, sandbox: true, backgroundThrottling: false }
  });
  inboxWindow.on('page-title-updated', event => event.preventDefault());
  return inboxWindow;
}

function openInboxSite(template, email) {
  const win = getInboxWindow();
  win.loadURL(inboxUrl(template, email || 'test@example.com'));
  win.show(); win.focus();
}

async function readInbox(url) {
  const win = getInboxWindow();
  await win.loadURL(url).catch(() => {});
  await sleep(1500); // inbox pages often fill the list with JavaScript after load
  const text = await win.webContents.executeJavaScript('document.body ? document.body.innerText : ""').catch(() => '');
  if (findCodes(text).length) return text;
  // The list may only show subjects: open the newest message that looks like the Meta/Muse mail.
  const opened = await win.webContents.executeJavaScript(`(() => {
    const link = [...document.querySelectorAll('a, [role="link"], tr, li')].find(el => /meta|muse|code|mã/i.test(el.innerText || ''));
    if (!link) return false;
    link.click(); return true;
  })()`).catch(() => false);
  if (!opened) return text;
  await sleep(2500);
  return win.webContents.executeJavaScript('document.body ? document.body.innerText : ""').catch(() => text);
}

// Runs in the Muse page. Returns which step the page is on.
const PAGE_STATE = `(() => {
  const visible = el => el && el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden' && !el.disabled;
  const inputs = [...document.querySelectorAll('input')].filter(visible);
  const label = el => [el.getAttribute('placeholder'), el.getAttribute('aria-label'), el.name, el.id, el.autocomplete].join(' ');
  const codeBoxes = inputs.filter(el => el.autocomplete === 'one-time-code' || /code|otp|verif|mã/i.test(label(el))
    || (el.inputMode === 'numeric' && !/phone|mobile|email/i.test(label(el))) || (el.maxLength === 1 && /^(text|tel|number)$/.test(el.type)));
  if (codeBoxes.length) return 'code';
  if (inputs.some(el => el.type === 'email' || /email|mobile number/i.test(label(el)))) return 'email';
  if ([...document.querySelectorAll('textarea')].some(visible)) return 'chat';
  return 'other';
})()`;

const FOCUS_EMAIL = `(() => {
  const visible = el => el && el.getClientRects().length && !el.disabled;
  const label = el => [el.getAttribute('placeholder'), el.getAttribute('aria-label'), el.name, el.id].join(' ');
  const input = [...document.querySelectorAll('input')].filter(visible).find(el => el.type === 'email' || /email|mobile number/i.test(label(el)));
  if (!input) return false;
  input.focus(); input.select(); return true;
})()`;

const FOCUS_CODE = `(() => {
  const visible = el => el && el.getClientRects().length && !el.disabled;
  const label = el => [el.getAttribute('placeholder'), el.getAttribute('aria-label'), el.name, el.id, el.autocomplete].join(' ');
  const boxes = [...document.querySelectorAll('input')].filter(visible).filter(el => el.autocomplete === 'one-time-code' || /code|otp|verif|mã/i.test(label(el))
    || (el.inputMode === 'numeric' && !/phone|mobile|email/i.test(label(el))) || (el.maxLength === 1 && /^(text|tel|number)$/.test(el.type)));
  if (!boxes.length) return false;
  boxes[0].focus(); boxes[0].select?.(); return true;
})()`;

// Clicks the form's submit/continue button; Enter is the fallback.
const SUBMIT = `(() => {
  const visible = el => el && el.getClientRects().length && !el.disabled;
  const button = [...document.querySelectorAll('button[type="submit"], button, [role="button"]')].filter(visible)
    .find(el => el.type === 'submit' || /^(continue|next|confirm|verify|log in|sign in|tiếp tục|xác nhận)$/i.test((el.innerText || el.getAttribute('aria-label') || '').trim()));
  if (!button) return false;
  button.click(); return true;
})()`;

async function waitForState(wc, wanted, timeoutMs) {
  const end = Date.now() + timeoutMs;
  let state = 'other';
  while (Date.now() < end) {
    state = await wc.executeJavaScript(PAGE_STATE).catch(() => 'other');
    if (wanted.includes(state)) return state;
    await sleep(700);
  }
  return state;
}

async function typeText(wc, text) {
  for (const ch of String(text)) {
    wc.insertText(ch);
    await sleep(60);
  }
}

async function submit(wc) {
  if (!(await wc.executeJavaScript(SUBMIT).catch(() => false))) {
    wc.sendInputEvent({ type: 'keyDown', keyCode: 'Enter' });
    wc.sendInputEvent({ type: 'keyUp', keyCode: 'Enter' });
  }
}

// signIn({ wc, email, template, home, report }) -> true when Muse shows the chat box afterwards.
async function signIn({ wc, email, template, home, report }) {
  if (!email) throw new Error('This account has no email.');
  if (!template) throw new Error('Set the OTP inbox URL first.');
  const url = inboxUrl(template, email);

  report('Opening Muse sign-in…');
  let state = await waitForState(wc, ['email', 'code', 'chat'], 4000);
  if (state === 'chat') return true;
  if (state === 'other') {
    await wc.loadURL(home).catch(() => {});
    state = await waitForState(wc, ['email', 'code', 'chat'], 20000);
  }
  if (state === 'chat') return true;

  // Codes already in the inbox belong to earlier sign-ins; only a new one counts.
  report('Reading inbox before sending the code…');
  const oldCodes = new Set(findCodes(await readInbox(url)));

  if (state === 'email') {
    report('Entering email…');
    if (!(await wc.executeJavaScript(FOCUS_EMAIL))) throw new Error('Could not find the email box on the Muse page.');
    await typeText(wc, email);
    await sleep(300);
    await submit(wc);
    state = await waitForState(wc, ['code', 'chat'], 30000);
    if (state === 'chat') return true;
    if (state !== 'code') throw new Error('Muse did not ask for a code after the email. Open the window to see why.');
  }

  report('Waiting for the code email…');
  const end = Date.now() + CODE_TIMEOUT_MS;
  let code = null;
  while (!code && Date.now() < end) {
    await sleep(POLL_MS);
    code = findCodes(await readInbox(url)).find(item => !oldCodes.has(item)) || null;
  }
  if (!code) throw new Error(`No new code arrived at ${email} within ${CODE_TIMEOUT_MS / 1000}s.`);

  report('Entering code…');
  if (!(await wc.executeJavaScript(FOCUS_CODE))) throw new Error('Could not find the code box on the Muse page.');
  await typeText(wc, code);
  await sleep(500);
  if ((await wc.executeJavaScript(PAGE_STATE).catch(() => 'other')) === 'code') await submit(wc);
  return (await waitForState(wc, ['chat'], 40000)) === 'chat';
}

module.exports = { signIn, openInboxSite, inboxUrl, findCodes };
