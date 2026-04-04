# CLAUDE.md — oyagami-local（親神ローカル）

AI アシスタント向けプロジェクトガイドです。

## プロジェクト概要

知的障害・発達障害のある方の支援情報（ケアの暗黙知・禁忌事項・緊急連絡先など）を Neo4j グラフDBで管理し、ローカルLLM（Ollama）で分析・抽出を行うシステム。クラウドAPIを一切使用せず、個人情報をオンプレミスで完全管理する。隣接プロジェクト `../neo4j-agno-agent/` の機能をローカルLLM版として再実装したもの。

## アーキテクチャ

```
oyagami-local/               # モノリポ
├── backend/                 # FastAPI + Agno + Ollama
└── frontend/                # Next.js 15 + shadcn/ui + Tailwind CSS v4
```

- **バックエンド**: `backend/app/main.py` がエントリポイント。FastAPI + Agno フレームワーク。
- **フロントエンド**: `frontend/src/app/` に Next.js App Router のページが並ぶ。
- **データベース**: Neo4j 5.15。`../neo4j-agno-agent/docker-compose.yml` で起動する既存インスタンスを共用する。
- **LLM**: Ollama（`http://localhost:11434`）。モデルはタスク種別に応じてエージェントが使い分ける。

## 起動方法

```bash
# Neo4j（隣接プロジェクトの docker-compose を使用）
cd ~/Dev-Work/neo4j-agno-agent && docker-compose up -d

# バックエンド（ポート 8000）
cd ~/Dev-Work/oyagami-local/backend
uv run uvicorn app.main:app --reload --port 8000

# フロントエンド（ポート 3000）
cd ~/Dev-Work/oyagami-local/frontend
pnpm dev

# ワンコマンド起動
./scripts/setup.sh          # 全サービス起動
./scripts/setup.sh --stop   # 全停止
./scripts/setup.sh --status # 状態確認
```

## テスト

```bash
cd backend
uv run pytest tests/ -v
```

- パッケージ管理: **uv**（pip は使わない）
- フロントエンドのパッケージ管理: **pnpm**

## 主要ディレクトリ

| パス | 内容 |
|---|---|
| `backend/app/agents/` | Agno マルチエージェント（team.py がオーケストレーター） |
| `backend/app/routers/` | FastAPI ルーター（chat, clients, dashboard, narratives, quicklog, search, system） |
| `backend/app/lib/` | 共有ライブラリ（Neo4j 操作・embedding など） |
| `backend/app/schemas/` | Pydantic スキーマ定義 |
| `backend/app/config.py` | 設定管理（pydantic-settings、.env から読み込み） |
| `backend/tests/` | pytest テスト |
| `frontend/src/app/` | Next.js App Router のページ |
| `frontend/src/components/` | shadcn/ui ベースのコンポーネント |
| `frontend/src/hooks/` | カスタムフック |

## マルチエージェント構成

| エージェント | ファイル | モデル | 役割 |
|---|---|---|---|
| Coordinator | `agents/coordinator.py` | mistral-small | 意図分類・ルーティング（常駐） |
| Intake | `agents/intake.py` | deepseek-r1:70b | テキスト→JSON抽出（排他） |
| Validator | `agents/validator.py` | mistral-small | 論理検証・安全性チェック（常駐） |
| Analyst | `agents/analyst.py` | llama4 | 分析・支援方針策定（排他） |
| CypherGen | `agents/cypher_gen.py` | qwen3-coder:30b | Cypher クエリ生成（排他） |
| Team | `agents/team.py` | — | AgnoTeam オーケストレーター |

排他モデルは同時に1つしかロードされない。ModelManager がメモリ管理を担う。

## Neo4j スキーマ規約

`../neo4j-agno-agent/docs/NEO4J_SCHEMA_CONVENTION.md` に準拠する。

- **ノード**: PascalCase（例: `Client`, `NgAction`, `SupportLog`）
- **リレーション**: UPPER_SNAKE_CASE（例: `MUST_AVOID`, `HAS_KEY_PERSON`, `LOGGED`）
- **プロパティ**: camelCase（例: `riskLevel`, `nextRenewalDate`, `createdAt`）
- クエリは必ずパラメータ化（`$param`）してインジェクションを防ぐ
- 冪等性のために `MERGE` を使用する

主要ノード: `Client`, `NgAction`, `CarePreference`, `Condition`, `KeyPerson`, `Guardian`, `Hospital`, `Supporter`, `SupportLog`, `MeetingRecord`, `Certificate`

## 重要な制約

### Safety First
- 緊急時の情報取得は **LLM を経由しない**。Neo4j を直接検索して NgAction を返す。
- `NgAction` ノードの `riskLevel` は `LifeThreatening` > `Panic` > `Discomfort` の優先順位。

### データ完全性
- AI 抽出はテキストに存在しない情報を補完・推測してはならない（**No Fabrication**）。
- クライアント名は一意制約あり。登録前に `validate_client_uniqueness()` で確認する。

### モデル選択
- 環境変数（`.env`）でモデルを設定する。ハードコード禁止。
- モデル名は `config.py` の設定クラス経由で参照する。

### フロントエンド
- 日本語名の検索UIはテキスト入力を避け、あかさたな方式のボタンフィルタを使う（`st.text_input` 相当の IME 問題を回避するため）。
