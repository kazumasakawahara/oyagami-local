# oyagami-local（親神ローカル）

**親亡き後支援データベース — ローカルLLM版**

知的障害・発達障害のある方の支援情報を Neo4j グラフDBで管理し、ローカルLLM（Ollama）で分析・抽出を行うシステムです。  
現行の [neo4j-agno-agent](../neo4j-agno-agent/) プロジェクトの機能を、クラウドAPI不使用で実現します。

---

## 概要

親亡き後支援データベースは、知的障害・発達障害のある方の支援情報（ケアの暗黙知・禁忌事項・緊急連絡先など）を構造化してグラフDBに蓄積し、支援者が必要な情報に素早くアクセスできるシステムです。

本リポジトリはその **ローカルLLM版** であり、すべての推論・抽出処理を Ollama 上で動作するモデルで完結させます。個人情報を含む支援情報がクラウドに送信されることなく、完全にオンプレミス環境で運用できます。

---

## 主な特徴

- **完全ローカル動作** — クラウドAPIへのデータ送信なし。個人情報保護・GDPR/個人情報保護法対応
- **マルチエージェント構成（Agno Team）** — タスクの性質に応じて最適なモデルを自動選択するエージェント協調アーキテクチャ
- **ModelManager による自動切替** — 128GB 統合メモリ内でのモデルのロード/アンロードを自動管理
- **Next.js + shadcn/ui による業務向けモダンUI** — ダッシュボード、ナラティブ入力、クイックログ、AIチャット
- **Safety First** — 緊急時は LLM を経由せず Neo4j を直接検索し、禁忌事項（NgAction）を最優先で返却
- **Neo4j Browser風エコマップ** — React Flowでダーク背景＋円形カラーノードの支援ネットワーク可視化
- **ローカル音声文字起こし** — OpenAI Whisperで面談音声をテキスト化、embeddingで検索可能に

---

## アーキテクチャ

```
oyagami-local/
├── backend/    FastAPI + Agno + Ollama（REST API + WebSocket）
└── frontend/   Next.js 15 + shadcn/ui + Tailwind CSS v4
```

- **モノリポ構成** — backend と frontend を単一リポジトリで管理
- **バックエンド**: FastAPI + Agno フレームワーク + Ollama（ローカルLLM）
- **フロントエンド**: Next.js 15 + shadcn/ui + Tailwind CSS v4
- **データベース**: Neo4j 5.15（隣接プロジェクト `neo4j-agno-agent` の docker-compose を共用）
- **通信**: REST API（CRUD操作）+ WebSocket（AIチャット）

---

## マルチエージェント構成

| エージェント | モデル | サイズ | 役割 | 常駐/排他 |
|---|---|---|---|---|
| Coordinator | mistral-small | 14GB | 意図分類・ルーティング | 常駐 |
| Intake | deepseek-r1:70b | 42GB | テキスト→JSON抽出 | 排他 |
| Validator | mistral-small | 14GB | 論理検証・安全性チェック | 常駐 |
| Analyst | llama4 | 67GB | 分析・支援方針策定 | 排他 |
| CypherGen | qwen3-coder:30b | 18GB | Cypher クエリ生成 | 排他 |
| Embedding | nomic-embed-text | 0.3GB | ベクトル生成 | 常駐 |

**排他モデル**は同時に1つしかメモリにロードされません。Coordinator が入力の意図を分類し、適切な排他モデルへルーティングします。常駐モデル（Coordinator・Validator・Embedding）は常時ロード状態を維持します。

---

## 必要環境

- **OS**: macOS（Apple Silicon、128GB+ 統合メモリ推奨）
- **Python**: 3.12+（パッケージ管理: uv）
- **Node.js**: 20+（パッケージ管理: pnpm）
- **Ollama**: 最新版
  - 必須モデル: `mistral-small`, `nomic-embed-text`
  - 推奨モデル: `deepseek-r1:70b`, `llama4`, `qwen3-coder:30b`
- **Neo4j**: 5.15+（Docker）— `neo4j-agno-agent` の docker-compose を使用
- **ffmpeg**: 最新版（Whisper音声文字起こし用）

---

## セットアップ

```bash
# 前提: Neo4j が ~/Dev-Work/neo4j-agno-agent/ の docker-compose で起動済みであること
cd ~/Dev-Work/neo4j-agno-agent && docker-compose up -d

# Ollama モデルの準備
ollama pull mistral-small
ollama pull nomic-embed-text
# deepseek-r1:70b, llama4, qwen3-coder:30b は既にインストール済みの前提

# バックエンド
cd ~/Dev-Work/oyagami-local/backend
cp ../.env.example ../.env  # 必要に応じて値を編集
uv sync

# フロントエンド
cd ~/Dev-Work/oyagami-local/frontend
pnpm install
```

---

## 起動方法

```bash
# ターミナル1: バックエンド（ポート 8000）
cd ~/Dev-Work/oyagami-local/backend
uv run uvicorn app.main:app --reload --port 8000

# ターミナル2: フロントエンド（ポート 3000）
cd ~/Dev-Work/oyagami-local/frontend
pnpm dev

# ブラウザで http://localhost:3000 を開く
```

### ワンコマンド起動

`scripts/setup.sh` で全サービスを一括管理できます。

```bash
# フル起動（競合停止 → Neo4j → Ollama → Backend → Frontend）
./scripts/setup.sh

# 全停止
./scripts/setup.sh --stop

# 状態確認
./scripts/setup.sh --status
```

---

## 画面一覧

| 画面 | パス | 説明 |
|---|---|---|
| ダッシュボード | `/` | 統計・更新期限アラート・最近の活動 |
| ナラティブ入力 | `/narrative` | テキスト入力またはファイルアップロード（docx/xlsx/pdf/txt）→AI抽出→確認→登録の3ステップ |
| クイックログ | `/quicklog` | 30秒で日常記録 |
| クライアント一覧 | `/clients` | あかさたなフィルタ付き検索 |
| AIチャット | `/chat` | マルチエージェント対話（WebSocket） |
| LLM設定 | `/settings` | モデルロード/アンロード・メモリ監視 |
| セマンティック検索 | `/search` | ベクトル類似度による支援記録・ケア指示検索 |
| エコマップ | `/ecomap` | Neo4j Browser風グラフ表示で支援ネットワーク可視化 |
| 面談記録 | `/meetings` | 音声アップロード→Whisper文字起こし→Neo4j登録 |

---

## API エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/dashboard/stats` | ダッシュボード統計 |
| GET | `/api/dashboard/alerts` | 更新期限アラート一覧 |
| GET | `/api/clients` | クライアント一覧 |
| GET | `/api/clients/{name}` | クライアント詳細 |
| POST | `/api/narratives/extract` | ナラティブテキストからAI抽出 |
| POST | `/api/narratives/register` | 抽出データをDBに登録 |
| POST | `/api/quicklog` | クイックログ登録 |
| GET | `/api/search/fulltext` | 全文検索 |
| POST | `/api/search/semantic` | セマンティック検索（ベクトル類似度） |
| GET | `/api/ecomap/templates` | エコマップテンプレート一覧 |
| GET | `/api/ecomap/colors` | カテゴリカラーマッピング |
| GET | `/api/ecomap/{name}` | エコマップデータ生成 |
| POST | `/api/meetings/upload` | 音声ファイルアップロード・文字起こし |
| GET | `/api/meetings/{name}` | 面談記録一覧 |
| GET | `/api/system/status` | Ollama/Neo4j接続状態・ロード済みモデル |
| POST | `/api/system/models/{name}/load` | モデルのロード |
| POST | `/api/system/models/{name}/unload` | モデルのアンロード |
| POST | `/api/narratives/upload` | ファイルアップロード（docx/xlsx/pdf/txt） |
| POST | `/api/narratives/validate` | 抽出データのスキーマ検証 |
| POST | `/api/narratives/safety-check` | 安全性チェック |
| GET | `/api/clients/{name}/emergency` | 緊急情報（NgAction優先） |
| GET | `/api/clients/{name}/logs` | 支援記録一覧 |
| GET | `/api/dashboard/activity` | 最近の活動ログ |
| WS | `/api/chat/ws` | AIチャット（WebSocket） |

---

## テスト

```bash
cd backend
uv run pytest tests/ -v
```

---

## プロジェクト構成

```
oyagami-local/
├── .env.example            # 環境変数テンプレート
├── README.md               # このファイル
├── CLAUDE.md               # AI アシスタント向けガイド
├── scripts/
│   └── setup.sh            # ワンコマンド起動/停止スクリプト
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI エントリポイント
│   │   ├── config.py       # 設定管理（pydantic-settings）
│   │   ├── agents/         # Agno マルチエージェント
│   │   │   ├── team.py     # AgnoTeam オーケストレーター
│   │   │   ├── coordinator.py
│   │   │   ├── intake.py
│   │   │   ├── validator.py
│   │   │   ├── analyst.py
│   │   │   └── cypher_gen.py
│   │   ├── routers/        # FastAPI ルーター
│   │   │   ├── chat.py
│   │   │   ├── clients.py
│   │   │   ├── dashboard.py
│   │   │   ├── narratives.py
│   │   │   ├── quicklog.py
│   │   │   ├── search.py
│   │   │   └── system.py
│   │   ├── lib/            # 共有ライブラリ
│   │   │   ├── chunking.py     # テキストチャンキング
│   │   │   ├── transcription.py # Whisper音声文字起こし
│   │   │   └── ecomap.py       # エコマップデータ生成
│   │   ├── routers/        # FastAPI ルーター（続き）
│   │   │   ├── ecomap.py       # エコマップAPI
│   │   │   └── meetings.py     # 面談記録API
│   │   └── schemas/        # Pydantic スキーマ
│   ├── scripts/
│   │   └── backfill_embeddings.py  # 既存ノードへのembedding付与
│   ├── tests/              # pytest テスト
│   ├── pyproject.toml
│   └── uv.lock
└── frontend/
    ├── src/
    │   ├── app/            # Next.js App Router
    │   │   ├── page.tsx    # ダッシュボード
    │   │   ├── narrative/
    │   │   ├── quicklog/
    │   │   ├── clients/
    │   │   ├── chat/
    │   │   ├── settings/
    │   │   ├── search/
    │   │   ├── ecomap/
    │   │   └── meetings/
    │   ├── components/     # shadcn/ui コンポーネント
    │   ├── hooks/          # カスタムフック
    │   └── lib/            # ユーティリティ
    ├── e2e/                # Playwright E2Eテスト
    ├── package.json
    └── pnpm-lock.yaml
```

---

## 関連プロジェクト

- **[neo4j-agno-agent](../neo4j-agno-agent/)** — 現行版（Gemini / Claude API 使用）。本プロジェクトはこちらの Neo4j データベースを共用します。

---

## ライセンス

MIT
