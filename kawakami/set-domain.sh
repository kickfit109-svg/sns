#!/usr/bin/env bash
# 公開URLを一括で差し替えます。
# 使い方:  ./set-domain.sh https://kawakami-kazuki.jp
set -euo pipefail
cd "$(dirname "$0")"
NEW="${1:?新しいURLを指定してください（例: https://kawakami-kazuki.jp）}"
NEW="${NEW%/}"
OLD="https://kawakami-kazuki.netlify.app"
grep -rl "$OLD" --include='*.html' --include='*.xml' --include='*.txt' . | while read -r f; do
  sed -i.bak "s#${OLD}#${NEW}#g" "$f" && rm -f "$f.bak"
  echo "更新: $f"
done
