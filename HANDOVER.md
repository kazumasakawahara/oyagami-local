# HANDOVER — oyagami-local

> 2026-09-04 作成。環境まわりの申し送りのみ。作業履歴は git log と CLAUDE.md / README.md を参照。
> Neo4j 本体はこのリポジトリにはない（`.env` 冒頭コメントのとおり別リポジトリの compose で起動）。

## Neo4j 認証の置き場（2026-09-04）

- Neo4j 認証の正典は `~/.config/nest/neo4j.env`（`NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` の3行、chmod 600）。各リポジトリの `.env` にはもう書かない（`NEO4J_LIVELIHOOD_*` は対象外で従来どおり `.env`）。
- `~/.zshrc` が `set -a` で読み込むので、シェルから起動するプロセスと `docker compose` の `${NEO4J_USERNAME}` / `${NEO4J_PASSWORD}` 展開はこれで賄う。未設定のまま `docker compose` を実行すると `:?` で止まる（`see ~/.config/nest/neo4j.env`）。
- パスワード変更は `project/nest-support/scripts/rotate_password.py`（`uv run python scripts/rotate_password.py`）。DB 側の `ALTER CURRENT USER SET PASSWORD` と正典ファイルの書き換えを一括で行い、値は表示しない。実行後は開いているシェルで `source ~/.config/nest/neo4j.env` し直す。
- compose の `NEO4J_AUTH` は初回起動時（データディレクトリが空のとき）にしか効かない。既存データの DB のパスワードは compose ではなく rotate_password.py で変える。
