# Ubuntu-LS Monitor

[![CI/CD Pipeline](https://github.com/zyuuuukak1n/ubuntu-ls_monitor/actions/workflows/main.yml/badge.svg)](https://github.com/zyuuuukak1n/ubuntu-ls_monitor/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React: 18](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![WebAuthn / FIDO2](https://img.shields.io/badge/WebAuthn-FIDO2%20Passkey-4285F4?logo=fido&logoColor=white)](https://fidoalliance.org/)

Ubuntu自宅サーバー向けに、稼働システムの可視化・リソース監視・限定的な制御を行うWeb管理ダッシュボードです。  
Cloudflare Tunnel経由での安全なアクセスを前提とし、**パスキー（WebAuthn/FIDO2）による完全パスワードレス認証**と**最小権限の原則に基づくサンドボックス設計**を徹底しています。

---

## 🌟 主な特徴

- 🔑 **パスキー（WebAuthn/FIDO2）認証**:
  - パスワードを一切保持・送信しない完全ハードウェア保護認証（Touch ID, Windows Hello, YubiKey対応）。
  - クローン攻撃検知（Sign Count検証）、60秒単一消費チャレンジ、リプレイ攻撃遮断。
  - **招待制ブートストラップ**: オープン登録を完全廃止し、サーバーCLI（`manage.py create-invite`）で発行された15分有効のワンタイムトークンでのみ初回登録可能。
  - マルチ認証器管理（複数デバイスの追加登録・名前変更・削除）。
- 📊 **リアルタイム・リソース監視**:
  - CPU（使用率、ロードアベレージ、温度センサー）、メモリ・スワップ、ディスク容量・I/O、ネットワーク送受信帯域。
  - 上位リソース消費プロセスリスト。
  - **Page Visibility API 連動**: ブラウザのバックグラウンドタブ時はSSEストリームを自動一時停止し、サーバー負荷と通信帯域を最小化。
- 🛡️ **最小権限サンドボックス制御**:
  - バックエンドプロセスは専用の非特権一般ユーザー（`dashboard-agent`）で実行（プロセス全体のroot起動を完全排除）。
  - ホワイトリスト（`config.yaml`）に完全一致したsystemdサービスおよびDockerコンテナのみ再起動可能。
  - 特権コマンドは `/etc/sudoers.d/dashboard` で引数レベルまで固定。
  - サーバー本体の再起動にはUI上で明示的な "REBOOT" 入力を要求する二重確認を強制。
- 📝 **セキュア設定ファイルエディタ**:
  - Web画面上で設定ファイル（`cloudflared/config.yml` 等）を閲覧・編集可能。
  - パストラバーサル（`../`）を厳格に遮断。
  - 保存時に `.bak.<timestamp>` を自動生成。
  - 構文チェック（Dry-run）合格時のみアトミック適用（構文エラー時は自動ロールバック）。
- 📑 **リアルタイムログストリーミング**:
  - `journalctl` および Docker コンテナの最新ログをWebコンソール上でSSEリアルタイムストリーミング。
- 🔒 **防御的設計と監査ログ**:
  - 誰が・いつ・どのIPから・どの操作を行ったかを構造化JSON（`audit.jsonl`）で永続化。

---

## 🏗️ アーキテクチャ

```
[ User Browser (Passkey Client) ]
               │  (HTTPS / FQDN)
               ▼
      [ Cloudflare Tunnel ]
               │  (Locally-managed / Reverse Proxy)
               ▼
     [ Apache2 VirtualHost ]
               │  (127.0.0.1:8000)
               ▼
[ FastAPI + Uvicorn (dashboard-agent) ]
    ├── WebAuthn / Session Auth (SQLite 0600)
    ├── Metrics Collector (psutil / thermal)
    ├── Whitelist Controller (config.yaml)
    │     ├── Sudo Sandboxing (/etc/sudoers.d/dashboard)
    │     └── Docker Engine Socket
    └── Structured Audit Logger (logs/audit.jsonl)
```

---

## 🚀 クイックスタート（ローカル開発環境）

### 1. リポジトリのクローン
```bash
git clone https://github.com/zyuuuukak1n/ubuntu-ls_monitor.git
cd ubuntu-ls_monitor
```

### 2. バックエンドの起動
```bash
cd backend
python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows PowerShell
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp ../.env.example .env

# 初回DB初期化
python manage.py init-db

# 開発サーバー起動
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. フロントエンドの起動
別ターミナルで実行します:
```bash
cd frontend
npm install
npm run dev
```

ブラウザで `http://localhost:5173` にアクセスします。

### 4. 初回管理者の登録
サーバー側ターミナルで招待URLを発行します:
```bash
cd backend
python manage.py create-invite
```
出力されたURL（`http://localhost:5173/#invite=<token>`）にアクセスし、お使いの端末のパスキーを登録してください。

---

## 🧪 テスト実行

バックエンドの単体テスト（認証、パストラバーサル拒否、引数バリデーション、バックアップ検証等）を実行します:

```bash
pytest backend/tests -v
```

---

## 📖 本番環境デプロイ手順

- **公開用汎用手順書**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) をご覧ください。

---

## 📜 ライセンス

MIT License © 2026 じゅーかきん  
詳細は [LICENSE](LICENSE) をご覧ください。
