# 小林凛太郎 プロキックボクシング教室（八王子・kickfit109）公式ページ

プロ格闘家 **小林凛太郎** のトレーニング受付を兼ねた公式サイト（静的サイト）です。
八王子 kickfit109 でのキックボクシング／ムエタイ教室の案内と、LINE 受付動線をまとめています。

## 構成

```
rintaro/
├── index.html         … 1ページ完結の公式ページ（SEO/OGP/構造化データ入り）
├── assets/
│   ├── style.css      … スタイル（ダーク×レッドのスタイリッシュ設計・レスポンシブ）
│   ├── main.js        … スクロール演出・年号自動更新
│   └── img/           … 本人写真（portrait / ring / rws / belt）
└── README.md
```

## 掲載内容

- **選手紹介**：RWS JAPAN・BOM（The Battle of Muay Thai）で戦う現役プロ
- **戦歴・獲得タイトル**：ハイライト＋公式リンク（最新の全戦績は下記の公式へ）
- **トレーニング案内**
  - 土曜日 19:00〜／日曜日 19:00〜
  - 月4回コース ¥8,800（kickfit109 会員は ¥5,500）
  - パーソナル 1回 ¥5,500
- **受付動線**：kickfit109 公式LINE にて「**凛太郎希望**」と送信
  - LINE: https://lin.ee/SqrWydz

## 公式リンク

- Instagram: https://www.instagram.com/rintarou7996
- RWS JAPAN 選手ページ: https://rwsjapan.com/fighter/rintaro-kobayashi/

## 公開方法

ビルド不要の静的サイトです。`rintaro/` 配下をそのまま任意のホスティング
（GitHub Pages / Netlify / Vercel / 既存サーバー等）に配置すれば公開できます。

ローカル確認：
```bash
cd rintaro
python3 -m http.server 8000
# → http://localhost:8000
```

## 更新時のメモ

- 戦績・タイトルは試合ごとに更新されます。正確な最新情報は上記 Instagram / RWS 公式を参照。
- 料金・スケジュール変更時は `index.html` の該当セクションと構造化データ（`SportsActivityLocation`）を更新してください。
- SEO ターゲット：**小林凛太郎 / 八王子 / プロキックボクシング**
