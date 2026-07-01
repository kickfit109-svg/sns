# snsgrow — SNS成長パターン学習 & 自動投稿ツール

Threads / X (旧Twitter) / note 向けに、**「伸びる投稿パターン」を学習** し、
Claude を使って各SNS最適化された投稿文を **自動生成 → プレビュー → 投稿** まで
一括で行う CLI ツールです。

## 特長

- **パターン学習**: 過去の投稿実績（CSV）を分析し、伸びた投稿に共通する
  特徴（フック・文字数・構成・投稿時間帯・ハッシュタグ等）を抽出します。
  実績が無くても、一般的な「伸びる型」の知識で補完します。
- **一括生成**: 1つのトピックから Threads / X / note それぞれの
  プラットフォーム特性に最適化した投稿を同時生成します。
- **投稿まで自動化**:
  - **X**: API v2 で自動投稿（スレッド対応）
  - **Threads**: Graph API で自動投稿
  - **note**: 公式投稿APIが無いため、コピペ用の下書き Markdown を出力
- **安全設計**: APIキー未設定でも「下書きモード」で全機能が動きます。
  自動投稿は必ずプレビュー確認 → 明示的な承認後に実行します。

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # 必要なAPIキーを記入（任意）
```

## 使い方

### 1. 伸びるパターンを学習する

```bash
# 過去投稿の実績CSVから学習
python -m snsgrow learn --input data/my_posts.csv --platform x

# 学習結果（パターンプロファイル）を確認
python -m snsgrow patterns
```

CSV フォーマット例は `data/sample_posts.csv` を参照してください。

### 2. 投稿を生成する

```bash
# トピックから3媒体分を一括生成（下書き）
python -m snsgrow generate --topic "副業で月5万稼ぐ方法" --platform all

# 生成結果は out/ 以下に保存されます
```

### 3. 投稿する

```bash
# 生成済みの下書きをプレビューして投稿
python -m snsgrow post --draft out/latest.json --platform x

# 予約投稿（最適な時間帯に投稿）
python -m snsgrow post --draft out/latest.json --platform x --schedule optimal
```

## 環境変数（.env）

| 変数 | 用途 |
|------|------|
| `ANTHROPIC_API_KEY` | 投稿文の生成に使用（必須） |
| `X_API_KEY` / `X_API_SECRET` / `X_ACCESS_TOKEN` / `X_ACCESS_SECRET` | X自動投稿（任意） |
| `THREADS_ACCESS_TOKEN` / `THREADS_USER_ID` | Threads自動投稿（任意） |

キーが未設定のプラットフォームは自動的に「下書きモード」になります。

## 注意事項

- note は公式の投稿APIが提供されていないため、自動投稿は非対応です
  （利用規約・アカウント保護の観点からブラウザ自動操作も既定では行いません）。
  生成した下書きをコピペして投稿してください。
- 各SNSの API 利用規約・レート制限を必ず遵守してください。
