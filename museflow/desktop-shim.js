// Desktop build: app.js was written for the extension's chrome.* API; map the parts it uses.
window.chrome = window.chrome || {};
window.chrome.runtime = window.museChrome.runtime;
window.chrome.storage = window.museChrome.storage;
