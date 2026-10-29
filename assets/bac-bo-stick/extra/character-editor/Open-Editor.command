#!/bin/zsh
# Double-click in Finder to start or reopen the local editor.
cd -- "$(dirname -- "$0")" || exit 1
if curl --max-time 2 -fsS 'http://127.0.0.1:8766/api/configs' >/dev/null 2>&1; then
  open 'http://127.0.0.1:8766'
else
  python3 serve.py --open
fi
