#!/usr/bin/env bash
#
# oyagami-local セットアップスクリプト
#
# 使い方:
#   ./scripts/setup.sh          # フル起動（Neo4j + Backend + Frontend）
#   ./scripts/setup.sh --stop   # 全停止
#   ./scripts/setup.sh --status # 状態確認
#
set -euo pipefail

# ─────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NEO4J_PROJECT="${PROJECT_ROOT}/../neo4j-agno-agent"
NEO4J_CONTAINER="support-db-neo4j"

# このプロジェクトが使うポート
PORTS=(7474 7687 8000 3000)

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ─────────────────────────────────────────────
# ポート競合チェック & 停止
# ─────────────────────────────────────────────
stop_conflicting_containers() {
    info "ポート競合のある Docker コンテナを確認中..."

    for port in "${PORTS[@]}"; do
        # このポートを使っているコンテナを検索
        containers=$(docker ps --format '{{.ID}} {{.Names}} {{.Ports}}' 2>/dev/null | grep ":${port}->" | awk '{print $1 " " $2}' || true)
        if [ -n "$containers" ]; then
            while IFS= read -r line; do
                cid=$(echo "$line" | awk '{print $1}')
                cname=$(echo "$line" | awk '{print $2}')
                # Neo4j コンテナは停止しない（後で起動するため）
                if [ "$cname" = "$NEO4J_CONTAINER" ]; then
                    continue
                fi
                warn "ポート ${port} を使用中: ${cname} (${cid}) → 停止します"
                docker stop "$cid" >/dev/null 2>&1 || true
                ok "停止: ${cname}"
            done <<< "$containers"
        fi
    done

    # ポートを直接使っているプロセスもチェック（Docker 以外）
    for port in 8000 3000; do
        pid=$(lsof -ti :"$port" 2>/dev/null || true)
        if [ -n "$pid" ]; then
            pname=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
            warn "ポート ${port} を使用中: ${pname} (PID: ${pid}) → 停止します"
            kill "$pid" 2>/dev/null || true
            ok "停止: ${pname} (PID: ${pid})"
        fi
    done

    ok "ポート競合チェック完了"
}

# ─────────────────────────────────────────────
# Neo4j 起動
# ─────────────────────────────────────────────
start_neo4j() {
    info "Neo4j コンテナを確認中..."

    if ! command -v docker &>/dev/null; then
        err "Docker がインストールされていません"
        exit 1
    fi

    if ! docker info &>/dev/null; then
        err "Docker デーモンが起動していません。Docker Desktop を起動してください。"
        exit 1
    fi

    # 既に起動中か確認
    if docker ps --format '{{.Names}}' | grep -q "^${NEO4J_CONTAINER}$"; then
        ok "Neo4j は既に起動中です"
    else
        # 停止中のコンテナがあれば再起動
        if docker ps -a --format '{{.Names}}' | grep -q "^${NEO4J_CONTAINER}$"; then
            info "停止中の Neo4j コンテナを再起動..."
            docker start "$NEO4J_CONTAINER"
        else
            # docker-compose で新規起動
            if [ ! -f "${NEO4J_PROJECT}/docker-compose.yml" ]; then
                err "docker-compose.yml が見つかりません: ${NEO4J_PROJECT}/docker-compose.yml"
                exit 1
            fi
            info "Neo4j コンテナを起動中..."
            (cd "$NEO4J_PROJECT" && docker compose up -d neo4j)
        fi

        # 起動待ち（最大30秒）
        info "Neo4j の起動を待機中..."
        for i in $(seq 1 30); do
            if curl -sf http://localhost:7474 >/dev/null 2>&1; then
                break
            fi
            sleep 1
            printf "."
        done
        echo ""
        ok "Neo4j 起動完了 (http://localhost:7474)"
    fi
}

# ─────────────────────────────────────────────
# Ollama 確認
# ─────────────────────────────────────────────
check_ollama() {
    info "Ollama を確認中..."

    if ! command -v ollama &>/dev/null; then
        err "Ollama がインストールされていません。https://ollama.com からインストールしてください。"
        exit 1
    fi

    if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        warn "Ollama が起動していません。起動を試みます..."
        ollama serve &>/dev/null &
        sleep 3
        if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
            err "Ollama の起動に失敗しました。手動で起動してください。"
            exit 1
        fi
    fi

    ok "Ollama 稼働中"

    # 必須モデルの確認
    local required_models=("mistral-small" "nomic-embed-text")
    local missing=()
    for model in "${required_models[@]}"; do
        if ! ollama list 2>/dev/null | grep -q "$model"; then
            missing+=("$model")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        warn "未インストールの必須モデル: ${missing[*]}"
        for model in "${missing[@]}"; do
            info "  ${model} をダウンロード中..."
            ollama pull "$model"
            ok "  ${model} インストール完了"
        done
    else
        ok "必須モデル確認済み (mistral-small, nomic-embed-text)"
    fi
}

# ─────────────────────────────────────────────
# バックエンド起動
# ─────────────────────────────────────────────
start_backend() {
    info "バックエンドを起動中 (port 8000)..."

    if ! command -v uv &>/dev/null; then
        err "uv がインストールされていません。https://docs.astral.sh/uv/ からインストールしてください。"
        exit 1
    fi

    # .env 確認
    if [ ! -f "${PROJECT_ROOT}/.env" ]; then
        if [ -f "${PROJECT_ROOT}/.env.example" ]; then
            cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
            warn ".env.example から .env をコピーしました。必要に応じて編集してください。"
        else
            err ".env ファイルが見つかりません"
            exit 1
        fi
    fi

    # 依存関係のインストール確認
    if [ ! -d "${PROJECT_ROOT}/backend/.venv" ]; then
        info "バックエンドの依存関係をインストール中..."
        (cd "${PROJECT_ROOT}/backend" && uv sync)
    fi

    # バックグラウンドで起動
    (cd "${PROJECT_ROOT}/backend" && uv run uvicorn app.main:app --reload --port 8000) &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "${PROJECT_ROOT}/.backend.pid"

    # 起動待ち
    for i in $(seq 1 15); do
        if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
            break
        fi
        sleep 1
        printf "."
    done
    echo ""
    ok "バックエンド起動完了 (http://localhost:8000)"
}

# ─────────────────────────────────────────────
# フロントエンド起動
# ─────────────────────────────────────────────
start_frontend() {
    info "フロントエンドを起動中 (port 3000)..."

    if ! command -v pnpm &>/dev/null; then
        err "pnpm がインストールされていません。npm install -g pnpm を実行してください。"
        exit 1
    fi

    # 依存関係の確認
    if [ ! -d "${PROJECT_ROOT}/frontend/node_modules" ]; then
        info "フロントエンドの依存関係をインストール中..."
        (cd "${PROJECT_ROOT}/frontend" && pnpm install)
    fi

    # バックグラウンドで起動
    (cd "${PROJECT_ROOT}/frontend" && pnpm dev) &
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" > "${PROJECT_ROOT}/.frontend.pid"

    sleep 3
    ok "フロントエンド起動完了 (http://localhost:3000)"
}

# ─────────────────────────────────────────────
# 全停止
# ─────────────────────────────────────────────
stop_all() {
    info "全サービスを停止中..."

    # バックエンド停止
    if [ -f "${PROJECT_ROOT}/.backend.pid" ]; then
        pid=$(cat "${PROJECT_ROOT}/.backend.pid")
        kill "$pid" 2>/dev/null && ok "バックエンド停止 (PID: ${pid})" || true
        rm -f "${PROJECT_ROOT}/.backend.pid"
    fi
    # ポートで残っているプロセスも停止
    lsof -ti :8000 2>/dev/null | xargs kill 2>/dev/null || true

    # フロントエンド停止
    if [ -f "${PROJECT_ROOT}/.frontend.pid" ]; then
        pid=$(cat "${PROJECT_ROOT}/.frontend.pid")
        kill "$pid" 2>/dev/null && ok "フロントエンド停止 (PID: ${pid})" || true
        rm -f "${PROJECT_ROOT}/.frontend.pid"
    fi
    lsof -ti :3000 2>/dev/null | xargs kill 2>/dev/null || true

    # Neo4j 停止
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${NEO4J_CONTAINER}$"; then
        docker stop "$NEO4J_CONTAINER" >/dev/null
        ok "Neo4j 停止"
    fi

    ok "全サービス停止完了"
}

# ─────────────────────────────────────────────
# 状態確認
# ─────────────────────────────────────────────
show_status() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  oyagami-local サービス状態"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Neo4j
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${NEO4J_CONTAINER}$"; then
        ok "Neo4j        http://localhost:7474"
    else
        err "Neo4j        停止中"
    fi

    # Ollama
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        loaded=$(curl -sf http://localhost:11434/api/ps 2>/dev/null | python3 -c "import sys,json; models=json.load(sys.stdin).get('models',[]); print(', '.join(m['name'] for m in models) if models else 'なし')" 2>/dev/null || echo "確認不可")
        ok "Ollama       http://localhost:11434  ロード中: ${loaded}"
    else
        err "Ollama       停止中"
    fi

    # Backend
    if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
        ok "Backend      http://localhost:8000"
    else
        err "Backend      停止中"
    fi

    # Frontend
    if curl -sf http://localhost:3000 >/dev/null 2>&1; then
        ok "Frontend     http://localhost:3000"
    else
        err "Frontend     停止中"
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────
main() {
    echo ""
    echo "╔══════════════════════════════════╗"
    echo "║  oyagami-local セットアップ       ║"
    echo "╚══════════════════════════════════╝"
    echo ""

    case "${1:-}" in
        --stop)
            stop_all
            ;;
        --status)
            show_status
            ;;
        *)
            stop_conflicting_containers
            start_neo4j
            check_ollama
            start_backend
            start_frontend
            echo ""
            show_status
            echo "ブラウザで http://localhost:3000 を開いてください"
            echo "停止: ./scripts/setup.sh --stop"
            echo ""
            # フォアグラウンドで待機（Ctrl+C で全停止）
            trap 'stop_all; exit 0' INT TERM
            wait
            ;;
    esac
}

main "$@"
