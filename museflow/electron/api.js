// Local HTTP API so other tools (storyvid) can use the signed-in Muse accounts.
// Listens on 127.0.0.1 only and refuses browser requests (any Origin header), so web pages
// cannot spend Muse credits through it.
//
//   GET  /api/status                      -> { accounts: [...], ready }
//   POST /api/generate {mediaType, prompt, size, duration?, negative?, audio?, references?: [file], saveTo}
//                                         -> { ok, file, profileName, retried, error?, code? }
//   POST /api/chat {prompt, timeoutSec?}  -> { ok, text }
//   POST /api/stop                        -> { ok }
const http = require('node:http');
const fsp = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');

const IMAGE_EXT = { 'image/png': '.png', 'image/jpeg': '.jpg', 'image/webp': '.webp', 'image/gif': '.gif' };
const SAFE_RETRY = 'SAFE EQUIVALENT RETRY: The previous version could not be generated. Create a close, allowed alternative for the same scene now. Stay faithful to the script\'s story purpose, characters, relationship, setting, action, mood, visual style, framing, continuity, and requested duration/aspect ratio. Change only the specific detail that prevents generation, replacing it with the nearest safe equivalent. Keep this scene in the story; do not skip it or change what it needs to accomplish. Do not ask a follow-up question or ask permission; generate the alternative in this attempt. Follow all content and safety rules.';

function sizeInstruction(size) {
  const shape = size === '16:9' ? 'Use a wide landscape composition.' : size === '9:16' ? 'Use a tall portrait composition.'
    : size === '1:1' ? 'Use a square composition.' : size === '4:3' ? 'Use a standard landscape composition.' : 'Use a standard portrait composition.';
  return `Output aspect ratio: ${size}. Match this frame shape exactly. ${shape}`;
}

// Same wording the canvas uses (app.js), so API and canvas generations behave alike.
function composePrompt({ mediaType, prompt, size, duration, negative, audio, referenceCount }) {
  if (mediaType === 'video') {
    const sound = audio || 'Natural ambient sound and sound effects only; no music, no speech, no narration.';
    return `Create a ${size} aspect ratio video clip, ${duration} seconds long. ${sizeInstruction(size)}\n\nAUDIO: ${sound}`
      + (referenceCount ? `\n\nUse the attached reference image${referenceCount === 1 ? ' as the exact opening frame' : 's as visual guidance; image 1 is the exact opening frame'}.` : '')
      + `\n\nPrompt: ${prompt}` + (negative ? `\n\nAvoid: ${negative}` : '');
  }
  return 'Create exactly one still image. This is an image-generation request, not a video request. Do not create a video, animation, or sequence of frames.'
    + `\n\n${prompt}`
    + (referenceCount ? `\n\nUse the attached reference image${referenceCount === 1 ? '' : 's'} as visual guidance; follow the prompt while preserving relevant subject details.` : '')
    + `\n\n${sizeInstruction(size)}` + (negative ? `\n\nAvoid the following (negative prompt): ${negative}` : '');
}

async function fileToDataUrl(file) {
  const bytes = await fsp.readFile(file);
  const ext = path.extname(file).toLowerCase();
  const type = ext === '.png' ? 'image/png' : ext === '.webp' ? 'image/webp' : ext === '.gif' ? 'image/gif' : 'image/jpeg';
  return `data:${type};base64,${bytes.toString('base64')}`;
}

// Writes the generated media to saveTo (the extension follows the real media type) and returns the path.
async function saveResult(url, saveTo, mediaDirFile) {
  await fsp.mkdir(path.dirname(saveTo), { recursive: true });
  const base = saveTo.replace(/\.[a-z0-9]+$/i, '');
  if (mediaDirFile) {
    const target = base + path.extname(mediaDirFile);
    await fsp.copyFile(mediaDirFile, target);
    return target;
  }
  const match = /^data:([^;,]*)(;base64)?,(.*)$/s.exec(url || '');
  if (!match) throw new Error('Muse returned media that could not be saved locally.');
  const bytes = match[2] ? Buffer.from(match[3], 'base64') : Buffer.from(decodeURIComponent(match[3]));
  const target = base + (IMAGE_EXT[match[1]] || path.extname(saveTo) || '.png');
  await fsp.writeFile(target, bytes);
  return target;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0; const chunks = [];
    req.on('data', chunk => { size += chunk.length; if (size > 5e6) { reject(new Error('Request too large.')); req.destroy(); } else chunks.push(chunk); });
    req.on('end', () => { try { resolve(chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {}); } catch { reject(new Error('Body must be JSON.')); } });
    req.on('error', reject);
  });
}

function startApi({ port, listProfiles, runOnProfile, stopAll, mediaFilePath }) {
  const handlers = {
    'GET /api/status': async () => {
      const accounts = listProfiles();
      return { ok: true, accounts, ready: accounts.filter(p => p.status === 'ready').length };
    },
    'POST /api/generate': async body => {
      const mediaType = body.mediaType === 'video' ? 'video' : 'image';
      if (!String(body.prompt || '').trim()) throw new Error('prompt is required.');
      if (!body.saveTo || !path.isAbsolute(body.saveTo)) throw new Error('saveTo must be an absolute file path.');
      const references = await Promise.all((body.references || []).map(fileToDataUrl));
      const size = body.size || '16:9', duration = Number(body.duration) || 10;
      const prompt = composePrompt({ mediaType, prompt: body.prompt, size, duration, negative: body.negative, audio: body.audio, referenceCount: references.length });
      const request = { requestId: crypto.randomUUID(), prompt, mediaType, size, duration, referenceImages: references, timeoutSec: Number(body.timeoutSec) || 600, profileId: body.profileId };
      let reply = await runOnProfile({ ...request, type: 'MUSEFLOW_GENERATE' }, (request.timeoutSec + 60) * 1000);
      let retried = false;
      if (!reply?.ok && reply?.code === 'SCENE_REFUSED' && body.retryOnRefusal !== false) {
        retried = true;
        reply = await runOnProfile({ ...request, requestId: crypto.randomUUID(), prompt: `${prompt}\n\n${SAFE_RETRY}`, type: 'MUSEFLOW_GENERATE' }, (request.timeoutSec + 60) * 1000);
      }
      if (!reply?.ok) return { ok: false, code: reply?.code || 'MUSE_ERROR', error: reply?.error || 'Muse did not return media.', retried, profileName: reply?.profileName };
      const file = await saveResult(reply.url, body.saveTo, mediaFilePath(reply.url));
      return { ok: true, file, retried, profileName: reply.profileName };
    },
    'POST /api/chat': async body => {
      if (!String(body.prompt || '').trim()) throw new Error('prompt is required.');
      const timeoutSec = Number(body.timeoutSec) || 600;
      return runOnProfile({ type: 'MUSEFLOW_CHAT', requestId: crypto.randomUUID(), prompt: body.prompt, timeoutSec }, (timeoutSec + 60) * 1000);
    },
    'POST /api/stop': async () => { await stopAll(); return { ok: true }; }
  };

  const server = http.createServer(async (req, res) => {
    const send = (status, value) => { res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' }); res.end(JSON.stringify(value)); };
    if (req.headers.origin) return send(403, { ok: false, error: 'Browser requests are not allowed.' });
    const handler = handlers[`${req.method} ${req.url.split('?')[0]}`];
    if (!handler) return send(404, { ok: false, error: 'Not found.' });
    if (req.method === 'POST' && !/application\/json/i.test(req.headers['content-type'] || '')) return send(415, { ok: false, error: 'Send JSON.' });
    try { send(200, await handler(req.method === 'POST' ? await readBody(req) : {})); }
    catch (error) { send(500, { ok: false, error: error.message || String(error) }); }
  });
  server.requestTimeout = 0; // generations can take many minutes
  server.listen(port, '127.0.0.1', () => console.log(`MuseFlow API on http://127.0.0.1:${port}`));
  server.on('error', error => console.error(`MuseFlow API could not start on port ${port}: ${error.message}`));
  return server;
}

module.exports = { startApi, composePrompt };
