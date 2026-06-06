# ローカル完結運用への移植計画（LOCAL-ONLY MIGRATION PLAN）

> **目的**: oyagami-local を、クラウドAPI・隣接プロジェクト（neo4j-agno-agent）への依存なしに、**単体で完結してオフライン運用できる**状態へ移行するための段階的計画。
> **実施時期**: 急がない。**ローカルLLM（抽出・埋め込み・OCR）の品質が十分に上がった段階**で着手する（§6 のゲート条件参照）。本書はその日のための設計図。
> **作成**: 2026-06-06 / 状態: ドラフト（未着手）

---

## 1. 現状の棚卸し（ローカル vs 依存）

oyagami は既に大部分がローカル化されている。以下は 2026-06 時点の実測ベース。

| 機能 | 現状 | ローカル度 |
|---|---|---|
| ナラティブ抽出 | Agno マルチエージェント（Ollama: deepseek-r1:70b 等） | ✅ ローカル完結 |
| 分析・支援方針 | Analyst（llama4） | ✅ ローカル完結 |
| 埋め込み生成 | `lib/embedding.py` → Ollama **nomic-embed-text（768次元）**。6本のベクトルインデックスは共通仕様と一致 | ✅ ローカル完結 |
| 音声文字起こし | `lib/transcription.py` → ローカル Whisper（ffmpeg 必須） | ✅ ローカル完結 |
| allowlist 検証 | `lib/db_operations.py`（MERGE_KEYS / ALLOWED_LABELS / ALLOWED_REL_TYPES） | ✅ あり（ただし §3 の差分要確認） |
| スキーマ正典 | `docs/SCHEMA_CONVENTION.md`（`~/Dev-Work/shared-schema/` から同期） | ✅ ローカル参照 |
| **Neo4j 本体** | **`../neo4j-agno-agent/docker-compose.yml` を共用**（自前 compose なし） | ⚠️ agno に依存 |
| **データ品質パイプライン（重複防止）** | normalize / sourceHash 冪等性 / セマンティック重複 / NgActionブロッキング / kanaファジー / CONDITION_ALIASES は **agno 側に厚い実装**。oyagami は簡易版の可能性 | ⚠️ 要移植（§4 Phase 2） |
| **埋め込みの整合性** | 共有DBには **agno/nest が書いた Gemini 埋め込み**が混在。oyagami の nomic ベクトルとは**別モデルで互換性なし** | ⚠️ 要再埋め込み（§4 Phase 3） |
| 画像・PDF の OCR | agno/nest は Gemini OCR。oyagami の `file_readers.py` のOCR対応は要確認 | ⚠️ ローカルOCR要検討（任意） |

**要点**: 「ゼロから作る」話ではない。oyagami は抽出・埋め込み・文字起こしを**すでにローカルで動かしている**。残るのは主に (A) DBの独立、(B) データ品質保証の本家並みへの引き上げ、(C) 埋め込みの整合、の3つ。

---

## 2. ゴール（完成状態の定義）

1. **ネットワークを切っても**、ナラティブ登録 → 検証 → 重複防止 → 埋め込み → セマンティック検索 → エコマップ → 面談文字起こし、が全て動く。
2. クラウドAPIキー（Gemini / Claude 等）を一切設定せずに起動・運用できる。
3. Neo4j を含め **oyagami 単体で起動・停止**できる（agno の有無に依存しない）。
4. 安全性の保証（NgAction の検出・重複ブロッキング・人間確認）が、クラウド版パイプラインと**同等**である。

---

## 3. 事前タスク（着手前にいつでもできる軽作業）

- [ ] **allowlist / MERGE キーを shared-schema v3.0 に整合**させる。現状の差分例:
  - `Certificate` の MERGE キー: oyagami `["type"]` → 正典は **複合 `["type","grade"]`**（療育手帳 A と B を別ノードに）
  - `CarePreference` の MERGE キー: oyagami `["category","instruction"]` → 正典の方針と突き合わせ
- [ ] `lib/db_operations.py` の allowlist と `GET /api/narrative/schema`（実行時権威）の差分を一覧化する。

---

## 4. 段階的移植プラン

### Phase 1: データベースの独立（依存を1つ断つ）

- [ ] oyagami 直下に **自前の `docker-compose.yml`** を新設（Neo4j 5.15、専用の named volume、ポートは当面 7687。agno と同時起動しないなら現行ポート流用可）。
- [ ] 起動スクリプト（`scripts/setup.sh`）を、agno の compose ではなく自前 compose を使うよう変更。
- [ ] **データ方針の決定**:
  - (a) **新規の空DBで再出発**（最もクリーン。検証データから運用データへ）／
  - (b) 既存データを `neo4j-admin dump` → 自前DBへ `load` で移送（運用データを引き継ぐ場合）。
- [ ] CLAUDE.md / README.md の「`neo4j-agno-agent` の compose を共用」という記述を更新。

> ねらい: これで oyagami の起動が agno の存在に依存しなくなる。

### Phase 2: データ品質パイプラインの移植（安全性の同等化）

agno の `lib/`（normalize・dedup・register）の堅牢な実装を oyagami の `backend/app/lib/db_operations.py` に取り込み、ローカル経路でもクラウド版と同等の品質保証を効かせる。

- [ ] **テキスト正規化**: NFC・全角半角・空白・敬称除去（`normalize_name` / `normalize_text` / `normalize_condition`）
- [ ] **CONDITION_ALIASES**（ASD→自閉症スペクトラム障害 等）の取り込み
- [ ] **sourceHash 冪等性**（SupportLog / MeetingRecord / LifeHistory / Wish）
- [ ] **MERGE キー戦略**（Certificate 複合キー、ServiceProvider は wamnetId 優先）
- [ ] **セマンティック重複検出**（NgAction は閾値超で **409 ブロッキング**＝確認必須、CarePreference は警告）
- [ ] **kana ファジーマッチ**（同音異字の人物重複検出）
- [ ] **登録前重複チェック**（agno の `/api/dedup/check` 相当をローカル関数として）

> ねらい: 「中・弱」経路に落ちないよう、ローカル書き込みでも **強制力 強** を維持。NgAction は安全に直結するため最優先。

### Phase 3: 埋め込みの整合と再埋め込み（モデル切替の本質）

埋め込みの生成自体は既にローカル（nomic-embed-text, 768次元）。問題は**ベクトルの出所が混在**しないこと。

- [ ] Phase 1 の独立DB内で、**全ノードを nomic で再埋め込み**（`backend/scripts/backfill_embeddings.py --all`）。Gemini 製ベクトルが残っていると検索・重複判定が壊れるため、**同一モデルで統一**する。
- [ ] 6本のベクトルインデックス（768次元 cosine）を独立DB上で再作成。
- [ ] 将来 **より優秀なローカル埋め込みモデル**へ乗り換える際は、(1) 次元が変わるならインデックス定義を更新、(2) **全件再埋め込み**、をセットで実施（モデルを跨いだベクトルは比較不可、という原則を厳守）。

### Phase 4: ローカル OCR / ビジョン（任意・後回し可）

- [ ] 画像・スキャンPDF の読み取りを、Gemini OCR からローカル手段（Tesseract、またはローカル視覚モデル）へ置換。
- [ ] 不要なら「テキスト・docx・xlsx のみ対応」と割り切る判断も可。

### Phase 5: 「クラウドの緒を切る」＋オフライン受け入れテスト

- [ ] `.env` から Gemini / Claude 等のキーを撤去し、コードのクラウド分岐が**キー無しで安全にスキップ/ローカルfallback**することを確認。
- [ ] **オフライン受け入れテスト**: 物理的にネットワークを遮断し、以下を一気通貫で実行して合格を確認。
  - ナラティブ登録（正規化・重複防止・NgActionブロッキングが効く）
  - セマンティック検索（nomic ベクトルで意味ヒット）
  - エコマップ生成 / 面談音声の文字起こし→登録
- [ ] nest の `tests/test_simulation_scenario.py` 相当のシナリオで、**クラウド版との結果パリティ**を比較。

---

## 5. 完了後に agno へ残る関係（重要）

oyagami が完全独立しても、**agno を即削除はしない**。理由:

- agno の `/api/narrative/intake` は **Hermes（gemini頭脳）からの書き込み経路**として現役。
- nest-support は別運用（Claude-Native）として継続。

oyagami のローカル完結は「oyagami が agno に依存しなくなる」ことであって、「agno が不要になる」ことではない。3者＋Hermes の共有DB構成を畳むかどうかは、別途の判断。

---

## 6. 着手のゲート条件（「LLMが優秀になったら」の具体化）

下記の品質が、安全運用に耐える水準に達したら着手する。判断は主観でなく**パリティ測定**で行う。

| 判定軸 | 現行（クラウド）基準 | ローカル候補 | ゲート |
|---|---|---|---|
| 日本語ナラティブ抽出の正確性（特に **NgAction / CarePreference の分類**） | Claude / Gemini | deepseek-r1:70b ほか後継 | 安全項目（NgAction）の取りこぼし・誤分類が許容水準以下 |
| 埋め込みの意味的品質（重複判定・検索） | Gemini Embedding 2 | nomic-embed-text ／後継 | 重複検出・検索の再現率/適合率がクラウド版と同等 |
| OCR / 手書き読み取り | Gemini OCR | ローカル視覚モデル | 任意。未達なら Phase 4 を見送り |

> **安全原則**: ローカル化のために**安全性の基準を下げない**。NgAction の検出・ブロッキング・人間確認（human-in-the-loop）は、クラウド版とのパリティが取れるまでカットオーバーしない。これは生命に関わるデータ（誤嚥・アレルギー等）を扱うため。

---

## 7. 推奨着手順序（サマリー）

1. §3 事前タスク（allowlist 整合）— いつでも可、軽い
2. **Phase 1（DB独立）** — 依存を1つ断つ最初の一歩。効果が大きく独立性も上がる
3. **Phase 2（品質パイプライン移植）** — 安全性の同等化。Phase 3 の前提
4. **Phase 3（再埋め込み）** — モデル統一。独立DB上で実施
5. Phase 4（ローカルOCR・任意）
6. **Phase 5（緒を切る＋オフライン受け入れテスト）** — ゲート条件（§6）を満たしてから

---

## 付記: 参照

- スキーマ正典: `docs/SCHEMA_CONVENTION.md`（`~/Dev-Work/shared-schema/` から同期）
- 実行時の allowlist 権威: agno `GET /api/narrative/schema`（ローカル完結後はローカル関数へ置換）
- 既存のローカル実装: `backend/app/lib/embedding.py`（nomic）, `transcription.py`（Whisper）, `db_operations.py`（allowlist）
- 移植元（厚い実装）: `neo4j-agno-agent/api/app/` および同 `lib/`（normalize・dedup・register_to_database）
