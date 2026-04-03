# oyagami-local セットアップガイド

このガイドでは、oyagami-local（親神ローカル）を初めて使う方向けに、環境構築から動作確認までを一つずつ丁寧に説明します。

**所要時間**: 30〜60分（モデルダウンロード時間を除く）

**完了後にできること**: ブラウザから障害福祉支援データベースにアクセスし、ローカルLLMによるテキスト抽出・分析・チャットが使えるようになります。クラウドAPIを一切使わないため、個人情報が外部に送信されることはありません。

---

## 目次

1. [必要なもの](#1-必要なもの)
2. [Homebrew のインストール](#2-ステップ1-homebrew-のインストール)
3. [Docker Desktop のインストール](#3-ステップ2-docker-desktop-のインストール)
4. [Ollama のインストール](#4-ステップ3-ollama-のインストール)
5. [Python環境（uv）のインストール](#5-ステップ4-python環境uvのインストール)
6. [Node.js環境（pnpm）のインストール](#6-ステップ5-nodejs環境pnpmのインストール)
7. [Neo4j データベースの起動](#7-ステップ6-neo4j-データベースの起動)
8. [oyagami-local のセットアップ](#8-ステップ7-oyagami-local-のセットアップ)
9. [起動と動作確認](#9-ステップ8-起動と動作確認)
10. [基本的な使い方](#10-基本的な使い方)
11. [よくある問題と解決法](#11-よくある問題と解決法)
12. [停止方法](#12-停止方法)
13. [次のステップ](#13-次のステップ)

---

## 1. 必要なもの

セットアップを始める前に、以下の要件を満たしていることを確認してください。

| 項目 | 要件 |
|------|------|
| **パソコン** | Mac（Apple Silicon: M1/M2/M3/M4） |
| **メモリ** | 128GB 推奨 / 64GB 最低 |
| **ストレージ空き容量** | 約 150GB（LLMモデルのダウンロード用） |
| **インターネット接続** | 初回セットアップ時のみ必要（以降はオフラインで動作） |

💡 **メモリについて**: 大規模なLLMモデル（deepseek-r1:70b や llama4）を動かすためには大容量メモリが必要です。64GBのマシンでは、同時に使えるモデル数が制限されますが、基本機能は動作します。

⚠️ **Intel Mac は非推奨です**: Ollama のローカルLLMはApple Siliconに最適化されています。Intel Mac では著しく遅くなる可能性があります。

---

## 2. ステップ1: Homebrew のインストール

Homebrew は Mac 向けのパッケージマネージャーです。後のステップで Node.js をインストールするために使います。

### 既にインストール済みか確認する

ターミナル（アプリケーション > ユーティリティ > ターミナル）を開いて、以下を入力してください。

```bash
brew --version
```

**インストール済みの場合の出力例**:

```
Homebrew 4.5.2
```

✅ バージョン番号が表示されたら、このステップは完了です。次のステップに進んでください。

### まだインストールしていない場合

以下のコマンドをターミナルに貼り付けて実行してください。

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

途中でパスワードの入力を求められます。Mac にログインする時のパスワードを入力してください（入力中は画面に何も表示されませんが、正常です）。

インストールが完了したら、ターミナルに表示される指示に従って PATH を設定してください。通常は以下のようなコマンドが表示されます。

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

設定後、`brew --version` でバージョンが表示されることを確認してください。

✅ Homebrew のインストール完了

---

## 3. ステップ2: Docker Desktop のインストール

Docker は、Neo4j データベースをコンテナとして動かすために使います。「コンテナ」とは、アプリケーションを隔離された環境で実行する仕組みです。

### インストール手順

1. ブラウザで [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/) を開く
2. 「Download for Mac - Apple Chip」を選択してダウンロード
3. ダウンロードした `.dmg` ファイルを開く
4. Docker アイコンを Applications フォルダにドラッグ
5. アプリケーションフォルダから Docker を起動する

💡 **初回起動時**: Docker Desktop は初期設定に少し時間がかかります。画面上部のメニューバーにクジラのアイコンが表示され、「Docker Desktop is running」と表示されるまで待ってください。

### 確認

```bash
docker --version
```

**期待される出力**:

```
Docker version 28.x.x, build xxxxxxx
```

✅ バージョン番号が表示されたら完了です。

### うまくいかない場合

| 症状 | 解決法 |
|------|--------|
| `docker: command not found` | Docker Desktop アプリを起動してください。メニューバーにクジラのアイコンが出るまで待ちます |
| `Cannot connect to the Docker daemon` | Docker Desktop が完全に起動するまで 1〜2分待ってから再度お試しください |

---

## 4. ステップ3: Ollama のインストール

Ollama は、ローカルでLLM（大規模言語モデル）を動かすためのランタイムです。ChatGPT のような AI をインターネット接続なしで使えるようにします。

### インストール手順

1. ブラウザで [https://ollama.com/download](https://ollama.com/download) を開く
2. 「Download for macOS」を選択
3. ダウンロードした `.zip` を展開し、Ollama アプリを Applications フォルダに移動
4. アプリケーションフォルダから Ollama を起動する

💡 **初回起動時**: メニューバーにラマのアイコンが表示されます。以降は Mac の起動時に自動で起動します。

### 確認

```bash
ollama --version
```

**期待される出力**:

```
ollama version is 0.x.x
```

### LLMモデルのダウンロード

oyagami-local は5つのモデルを使い分けます。以下のコマンドで順番にダウンロードしてください。

⚠️ **モデルのダウンロードには時間がかかります**。合計で約 140GB のダウンロードになります。安定したネットワーク環境で実行してください。

```bash
# 1. Coordinator / Validator 用（約14GB、5〜10分）
ollama pull mistral-small

# 2. Embedding 用（約0.3GB、1分以下）
ollama pull nomic-embed-text

# 3. テキスト抽出 用（約42GB、15〜30分）
ollama pull deepseek-r1:70b

# 4. 分析 用（約67GB、20〜40分）
ollama pull llama4

# 5. Cypher生成 用（約18GB、5〜15分）
ollama pull qwen3-coder:30b
```

💡 **最小構成で始めたい場合**: `mistral-small` と `nomic-embed-text` の2つだけでも基本的な動作確認ができます。他のモデルは後からダウンロードしても構いません。

### ダウンロード済みモデルの確認

```bash
ollama list
```

**期待される出力（全モデルダウンロード済みの場合）**:

```
NAME                   ID            SIZE      MODIFIED
mistral-small:latest   xxx...        14 GB     ...
nomic-embed-text:latest xxx...       274 MB    ...
deepseek-r1:70b        xxx...        42 GB     ...
llama4:latest          xxx...        67 GB     ...
qwen3-coder:30b        xxx...        18 GB     ...
```

✅ 必要なモデルが一覧に表示されていれば完了です。

---

## 5. ステップ4: Python環境（uv）のインストール

**uv** は Python のパッケージマネージャーです。従来の pip よりも高速で、プロジェクトごとに独立した Python 環境を自動で管理してくれます。

### インストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**インストール完了後、ターミナルを一度閉じて開き直してください**。これにより、uv コマンドが使えるようになります。

### 確認

```bash
uv --version
```

**期待される出力**:

```
uv 0.x.x
```

✅ バージョン番号が表示されたら完了です。

### うまくいかない場合

| 症状 | 解決法 |
|------|--------|
| `uv: command not found` | ターミナルを閉じて開き直してください |
| それでも見つからない | `source ~/.zshrc` を実行するか、新しいターミナルウィンドウを開いてください |

---

## 6. ステップ5: Node.js環境（pnpm）のインストール

Node.js はフロントエンド（画面側）の動作に必要です。pnpm は Node.js のパッケージマネージャーで、npm より高速かつディスク効率が良いものです。

### Node.js のインストール

```bash
brew install node
```

**期待される出力の最後の部分**:

```
==> node
...
```

### 確認

```bash
node --version
```

**期待される出力**:

```
v22.x.x
```

### pnpm のインストール

```bash
npm install -g pnpm
```

### 確認

```bash
pnpm --version
```

**期待される出力**:

```
10.x.x
```

✅ `node` と `pnpm` の両方でバージョンが表示されたら完了です。

---

## 7. ステップ6: Neo4j データベースの起動

Neo4j はグラフデータベースです。人と人の関係、支援者と利用者の繋がりなど、「つながり」を中心としたデータの管理に適しています。

oyagami-local は、隣接プロジェクト `neo4j-agno-agent` の Docker 設定を使って Neo4j を起動します。

### 起動

```bash
cd ~/Dev-Work/neo4j-agno-agent && docker compose up -d
```

💡 `docker-compose`（ハイフン付き）でも `docker compose`（スペース区切り）でも動作しますが、新しいバージョンの Docker では `docker compose` が推奨されています。

**期待される出力**:

```
[+] Running 1/1
 ✔ Container support-db-neo4j  Started
```

### 起動の確認

Neo4j が完全に起動するまで 10〜30秒ほどかかります。以下のどちらかの方法で確認してください。

**方法1: ブラウザで確認**

ブラウザで [http://localhost:7474](http://localhost:7474) を開いてください。

Neo4j Browser の画面が表示されたら成功です。接続情報の入力を求められたら、以下を入力してください。

| 項目 | 値 |
|------|-----|
| Connect URL | `bolt://localhost:7687` |
| Username | `neo4j` |
| Password | `password` |

**方法2: コマンドで確認**

```bash
docker ps
```

`support-db-neo4j` というコンテナが `Up` の状態で表示されていれば成功です。

### うまくいかない場合

| 症状 | 原因 | 解決法 |
|------|------|--------|
| `Cannot connect to the Docker daemon` | Docker Desktop が起動していない | Docker Desktop アプリを起動してから再実行 |
| `Bind for 0.0.0.0:7687 failed: port is already allocated` | ポートが他のプロセスに使われている | `docker ps` で既存コンテナを確認し、`docker stop <コンテナ名>` で停止 |
| ブラウザで 7474 にアクセスできない | Neo4j がまだ起動中 | 30秒ほど待ってからリロード |

✅ Neo4j Browser にログインできたら完了です。

---

## 8. ステップ7: oyagami-local のセットアップ

いよいよ本体のセットアップです。

### 環境変数ファイルの作成

```bash
cd ~/Dev-Work/oyagami-local
cp .env.example .env
```

💡 `.env` ファイルにはデータベースの接続情報やモデル設定が含まれています。デフォルトのままで動作しますが、必要に応じてエディタで編集できます。

### バックエンドのセットアップ

```bash
cd ~/Dev-Work/oyagami-local/backend
uv sync
```

**期待される出力**: uv が Python 環境を作成し、依存パッケージを自動でインストールします。

```
Using CPython 3.12.x
Creating virtual environment at: .venv
Resolved XX packages in X.XXs
Prepared XX packages in X.XXs
Installed XX packages in X.XXs
 + agno==X.X.X
 + fastapi==X.X.X
 + neo4j==X.X.X
 ...
```

💡 **初回のみ時間がかかります**: Python のダウンロードとパッケージのインストールが行われるため、1〜3分ほどかかることがあります。

### フロントエンドのセットアップ

```bash
cd ~/Dev-Work/oyagami-local/frontend
pnpm install
```

**期待される出力**:

```
Lockfile is up to date, resolution step is skipped
Packages: +XXX
+++++++++++++++++++++++++++++++++++++++++
Progress: resolved XXX, reused XXX, downloaded X, added XXX, done
```

✅ 両方ともエラーなく完了したら、セットアップ完了です。

---

## 9. ステップ8: 起動と動作確認

3つのターミナルウィンドウ（またはタブ）を使って、それぞれ別のプロセスを起動します。

### ターミナル1: バックエンド（FastAPI）

```bash
cd ~/Dev-Work/oyagami-local/backend
uv run uvicorn app.main:app --reload --port 8000
```

**期待される出力**:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXXX] using StatReload
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

⚠️ バックエンドが完全に起動してからフロントエンドを起動してください。

### ターミナル2: フロントエンド（Next.js）

```bash
cd ~/Dev-Work/oyagami-local/frontend
pnpm dev
```

**期待される出力**:

```
  ▲ Next.js 16.x.x
  - Local:        http://localhost:3000
  - Environments: .env

 ✓ Starting...
 ✓ Ready in X.Xs
```

### 動作確認

以下の方法で、全体が正しく動作しているか確認してください。

**1. ヘルスチェック（バックエンドの確認）**

ブラウザで [http://localhost:8000/api/health](http://localhost:8000/api/health) を開くか、新しいターミナルで以下を実行してください。

```bash
curl http://localhost:8000/api/health
```

**期待される出力**:

```json
{"status": "ok"}
```

**2. フロントエンドの確認**

ブラウザで [http://localhost:3000](http://localhost:3000) を開いてください。

以下のような画面が表示されれば成功です。
- 左側にサイドバーのナビゲーション
- メインエリアにダッシュボード

**3. モデル状態の確認**

ブラウザで [http://localhost:3000/settings](http://localhost:3000/settings) を開いてください。

設定画面で各モデルの接続状態を確認できます。Ollama にダウンロード済みのモデルが一覧表示されます。

✅ 全ての確認が通れば、セットアップは完了です。

---

## 10. 基本的な使い方

### Dashboard（ダッシュボード）

統計情報の確認ができます。登録されているクライアント数、支援記録数、禁忌事項数などが一覧で表示されます。

### Narrative（ナラティブ入力）

自然文のテキストを入力すると、LLMが構造化されたデータに変換します。

1. テキストエリアに支援情報を入力する
2. AI がテキストからクライアント名・状態・禁忌事項などを自動抽出する
3. 抽出結果を確認する
4. 問題なければ「登録」でデータベースに保存する

### QuickLog（簡易記録）

日々の支援記録を手早く入力するための画面です。特筆すべきイベントがあったときに使います。

### Chat（AIチャット）

AI に自然言語で質問すると、データベースの情報を元に回答します。

💡 **初回のチャット送信時は30〜60秒ほどかかります**。Ollama がモデルをメモリにロードする時間が必要なためです。2回目以降はモデルがメモリに残っている間は即座に応答します。

### Settings（設定）

モデルの手動ロード・アンロードができます。メモリが不足している場合は、使わないモデルをアンロードすることで空き容量を確保できます。

---

## 11. よくある問題と解決法

| 症状 | 原因 | 解決法 |
|------|------|--------|
| Neo4j に接続できない | Docker が起動していない、またはコンテナが停止している | `docker ps` で確認し、停止していれば `cd ~/Dev-Work/neo4j-agno-agent && docker compose up -d` で再起動 |
| Ollama に接続できない | Ollama アプリが起動していない | メニューバーにラマのアイコンがあるか確認。なければ Applications から Ollama を起動 |
| モデルのロードが遅い | 初回はモデルをディスクからメモリに読み込むため時間がかかる | 正常な動作です。30〜60秒待ってください。モデルがメモリに残っている間は即座に応答します |
| メモリ不足でモデルが読み込めない | 大きいモデルが既にメモリを占有している | Settings 画面で不要なモデルをアンロードしてから再度試してください |
| フロントエンドが表示されない | バックエンドが起動していない | ターミナルでバックエンドが起動しているか確認。エラーがあれば解消してからフロントを起動 |
| `pnpm: command not found` | pnpm がインストールされていない、またはパスが通っていない | `npm install -g pnpm` を再実行してください |
| `uv: command not found` | uv のパスが通っていない | ターミナルを閉じて開き直してください。それでも解決しない場合は `source ~/.zshrc` を実行 |
| `curl: (7) Failed to connect to localhost port 8000` | バックエンドが起動していない | ターミナル1 でバックエンドを起動してください |
| ブラウザに「接続が拒否されました」と表示される | サーバーが起動していない | バックエンド・フロントエンドの両方が起動しているか確認してください |

---

## 12. 停止方法

使い終わったら、以下の手順で各サービスを停止してください。

### バックエンドとフロントエンドの停止

それぞれのターミナルで `Ctrl + C` を押してください。

### Neo4j の停止

```bash
cd ~/Dev-Work/neo4j-agno-agent && docker compose down
```

**期待される出力**:

```
[+] Running 1/1
 ✔ Container support-db-neo4j  Stopped
```

💡 データベースのデータは `neo4j-agno-agent/neo4j_data/` に保存されているため、停止してもデータが消えることはありません。

### Ollama の停止

Ollama はバックグラウンドで常駐しています。停止したい場合は、メニューバーのラマのアイコンから「Quit Ollama」を選択するか、以下のコマンドを実行してください。

```bash
killall ollama
```

💡 Ollama は起動していても大量のリソースを消費しません。モデルがメモリにロードされていなければ、常駐させたままでも問題ありません。

---

## 13. 次のステップ

セットアップお疲れさまでした。ここからは、以下のドキュメントで詳しい使い方や開発ガイドを確認できます。

| ドキュメント | 内容 |
|------------|------|
| `README.md` | プロジェクトの概要とAPI仕様 |
| `CLAUDE.md` | 開発者向けガイド（アーキテクチャ、エージェント構成、スキーマ規約） |

また、以下のことを試してみてください。

- **AIチャットで質問する**: 「利用者の一覧を表示して」「田中さんの禁忌事項を教えて」など、自然言語で支援情報を検索できます
- **ナラティブ入力を試す**: 面談記録や支援報告書のテキストをそのまま貼り付けて、AIによる構造化抽出を体験できます
- **Neo4j Browser でデータを見る**: [http://localhost:7474](http://localhost:7474) で直接 Cypher クエリを実行し、グラフ構造を視覚的に確認できます

何か問題がありましたら、[よくある問題と解決法](#11-よくある問題と解決法)を確認してください。
