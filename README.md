# Luminode Chat Server

#### リアルタイムチャットサーバー
Python/FastAPIとSocket.IOを使用したリアルタイムチャットサーバーの実装です。

## ⚙️ このリポジトリについて
ここでは具体的なサーバー実装を扱います。Luminode全体のドキュメントは[こちら](https://github.com/Luminode-Project/Luminode)を参照してください。

## 仕様
### ✨ データ処理の流れ
<img src="https://i.gyazo.com/497a093c2c2032d76fb1e44cd49d1b59.png" alt="仕様" align="right" width="30%" />

1. connection → receiver（send）: クライアントからのメッセージ/イベントを受信
2. receiver → model（call）: 操作の呼び出し（検証・権限確認）
3. model → sender（event call）: データベースの操作をリアルタイムに通知
4. receiver → sender（event）: データベースを通さないリアルタイム処理
5. sender → connection（send）: 対象接続/ルームへブロードキャスト

### メッセージ送信
Socket.IOのeventを使用してメッセージを送信します。
イベント毎の仕様は[メッセージイベント一覧](docs/message_events.md)を参照してください。

### データベース
データベースはMongoDB、ODMはBeanieを使用します。
データベースのスキーマは[データベーススキーマ一覧](docs/database_schemas.md)を参照してください。

### 認証
認証はJWTを使用します。
認証の仕様は[認証仕様](docs/authentication.md)を参照してください。

## どうやって使う？
### 開発時
```bash
pip install -r requirements.txt
```
```bash
uvicorn src.app:app_socketio --reload
```

### 本番時
本番環境でこちらサーバーの単体での実行は推奨されていません。代わりに[Luminode](https://github.com/Luminode-Project/Luminode)を参照し、利用してください。

---

*技術的な詳細やセットアップ手順については、[技術ドキュメント](docs/tech.md)をご覧ください。*