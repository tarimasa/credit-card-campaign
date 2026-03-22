# ARCHITECTURE-proto.md
## Credit Card Campaign Tracker - プロトタイプ実装指示書

---

## 概要

三井住友OliveゴールドのキャンペーンページをスクレイピングしLINEにPush通知する
最小構成のプロトタイプを実装する。

---

## 技術スタック

| 項目 | 内容 |
|---|---|
| 言語 | Python 3.11以上 |
| スクレイピング | Playwright |
| データ保存 | SQLite |
| 通知 | LINE Messaging API |
| スケジューラ | python-crontab または手動実行 |

---

## ディレクトリ構成
```
credit-card-campaign/
├── main.py                  # エントリーポイント
├── scraper/
│   └── olive_gold.py        # OliveゴールドのスクレイピングO処理
├── db/
│   └── database.py          # SQLite操作
├── notifier/
│   └── line_notify.py       # LINE通知処理
├── models/
│   └── campaign.py          # キャンペーンデータモデル
├── data/
│   └── campaigns.db         # SQLiteデータファイル（自動生成）
├── .env                     # 環境変数（LINE TokenなどO）
├── requirements.txt         # 依存パッケージ
└── README.md
```

---

## データモデル

### Campaignテーブル（SQLite）

| カラム名 | 型 | 内容 |
|---|---|---|
| id | INTEGER PRIMARY KEY | 自動採番 |
| card_name | TEXT | カード名（例：OliveゴールドO） |
| title | TEXT | キャンペーンタイトル |
| summary | TEXT | 要約 |
| max_amount | TEXT | 付与金額上限 |
| period | TEXT | キャンペーン期間 |
| conditions | TEXT | 付与条件 |
| campaign_url | TEXT | キャンペーンURL |
| thumbnail_url | TEXT | サムネイル画像URL |
| notified | BOOLEAN | 通知済みフラグ |
| created_at | DATETIME | 取得日時 |
| updated_at | DATETIME | 更新日時 |

---

## 実装指示

### 1. scraper/olive_gold.py

- Playwrightを使用してOliveゴールドのキャンペーンページを取得
- 対象URL：三井住友カードのキャンペーン一覧ページ
- 以下の情報を取得してCampaignモデルに格納すること
  - キャンペーンタイトル
  - キャンペーンURL
  - サムネイル画像URL
  - 付与金額上限（ページ内に記載がある場合）
  - キャンペーン期間
  - 付与条件
- JavaScriptレンダリングが必要なページを想定してPlaywrightを使用
- スクレイピング失敗時はエラーログを出力して処理を継続

### 2. db/database.py

- SQLiteを使用してCampaignテーブルを管理
- 以下の関数を実装すること
  - `init_db()` テーブルが存在しない場合に作成
  - `save_campaign(campaign)` キャンペーンを保存（重複はURLで判定）
  - `get_unnotified_campaigns()` 未通知のキャンペーン一覧を取得
  - `mark_as_notified(campaign_id)` 通知済みフラグを更新
- キャンペーンURLをユニークキーとして重複登録を防ぐ

### 3. notifier/line_notify.py

- LINE Messaging APIを使用してFlex Messageで通知
- 以下の構成でカード形式のメッセージを送信すること
```
┌─────────────────────┐
│ [サムネイル画像]      │
│ キャンペーンタイトル  │
│ 期間：〇〇〜〇〇     │
│ 上限：〇〇円相当     │
│ 要約テキスト         │
│ [ キャンペーンに登録 ]│ ← タップでURLへ遷移
└─────────────────────┘
```

- 環境変数からLINE Channel Access TokenとUser IDを取得
- 送信失敗時はエラーログを出力

### 4. models/campaign.py

- Campaignデータクラスを定義
- 上記テーブル定義と同じフィールドを持つdataclassで実装

### 5. main.py

以下の順序で処理を実行すること
```
1. init_db()でDB初期化
2. olive_gold.py でスクレイピング実行
3. 取得したキャンペーンをDBに保存
4. 未通知キャンペーンを取得
5. LINE通知を送信
6. 通知済みフラグを更新
```

---

## 環境変数（.env）
```
LINE_CHANNEL_ACCESS_TOKEN=your_token_here
LINE_USER_ID=your_user_id_here
```

---

## requirements.txt に含めるパッケージ
```
playwright
python-dotenv
requests
```

---

## 実装時の注意事項

- `.env` は `.gitignore` に追加してGitHubにpushしないこと
- スクレイピング対象サイトへの負荷を避けるため
  リクエスト間隔は3秒以上空けること
- Playwrightは初回実行前に `playwright install chromium` が必要
- スクレイピング結果が取得できない場合は
  サイト構造が変わっている可能性があるためログに出力して終了

---

## 動作確認手順
```bash
# 1. パッケージインストール
pip install -r requirements.txt
playwright install chromium

# 2. .envファイルを作成してトークンを設定

# 3. 実行
python main.py
```

---

## 今後の拡張予定（プロトタイプ完成後）

- 対応カードをJCB W・J-Westに拡大
- Azure Functionsへの移植
- 締切3日前リマインド機能の追加
- パーソナライズ通知（保有カード設定）の追加
