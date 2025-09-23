# Luminode Chat Server

#### Realtime Messaging Server
Realtime messaging server implemented with Python/FastAPI and Socket.IO.

## ⚙️ About this repository
This repository handles the specific server implementation. Please refer to the parent repository [Luminode](https://github.com/Luminode-Project/Luminode) for the overall documentation.

## Specification
### ✨ Data Processing Flow
<img src="https://i.gyazo.com/497a093c2c2032d76fb1e44cd49d1b59.png" alt="Specification" align="right" width="30%" />

1. connection → receiver（send）: Receive messages/events from the client
2. receiver → model（call）: Call the operation (validation/permission check)
3. model → sender（event call）: Realtime notification of database operations
4. receiver → sender（event）: Realtime processing without going through the database
5. sender → connection（send）: Broadcast to the target connection/room

### Message Sending
Events in Socket.IO is used to send messages.
Please refer to [Message Events List](docs/message_events.md) for the specification of each event.

### Database
The database is MongoDB, and the ODM is Beanie.
Please refer to [Database Schema List](docs/database_schemas.md) for the schema of the database.

<!--
### Authentication
Authentication is using JWT.
Please refer to [Authentication Specification](docs/authentication.md) for the specification of authentication.
-->

## How to use?
### Development
```bash
pip install -r requirements.txt
```
```bash
uvicorn src.app:app_socketio --reload
```

### Production
It is not recommended to run this server alone in a production environment. Please refer to [Luminode](https://github.com/Luminode-Project/Luminode) for usage.

### README in other languages
- 🇯🇵 日本語版は[こちら](README-日本語.md)を参照してください。

---

*Please refer to [Technical Document](docs/tech.md) for technical details and setup instructions.*