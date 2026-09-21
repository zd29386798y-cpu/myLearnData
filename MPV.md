はい。今回は単なるディレクトリ案ではなく、**そのまま `C:\Projects\l2-trace-analyzer` に展開してMVP開発を開始できるパッケージ**として作りました。

PythonではWindowsを含むクロスプラットフォームのパス処理に `pathlib.Path` を使えるため、今回の構成でも採用しています。([Python documentation][1])

### パッケージ

[**l2-trace-analyzer-mvp.zip をダウンロード**](sandbox:/mnt/data/l2-trace-analyzer-mvp.zip)

---

# 1. ファイル構成

```text
C:\Projects\l2-trace-analyzer
│
├─ app.py
│
├─ config/
│   └─ config.yaml
│
├─ trace/
│   ├─ __init__.py
│   ├─ parser.py
│   ├─ normalizer.py
│   └─ correlation.py
│
├─ graph/
│   ├─ __init__.py
│   ├─ event_graph.py
│   ├─ task_graph.py
│   └─ dependency_graph.py
│
├─ knowledge/
│   ├─ __init__.py
│   ├─ functions.py
│   ├─ middleware.py
│   └─ rules.py
│
├─ decision/
│   ├─ __init__.py
│   ├─ laya.py
│   ├─ hypotheses.py
│   └─ evaluator.py
│
├─ analysis/
│   ├─ __init__.py
│   ├─ incident.py
│   ├─ rootcause.py
│   └─ evidence.py
│
├─ storage/
│   ├─ __init__.py
│   ├─ sqlite.py
│   └─ schema.sql
│
├─ ui/
│   ├─ __init__.py
│   └─ dashboard.py
│
├─ tests/
│   ├─ __init__.py
│   ├─ test_trace.py
│   ├─ test_graph.py
│   └─ test_rootcause.py
│
├─ requirements.txt
├─ README.md
└─ sample_trace.log
```

---

# 2. 各ファイルの役割

## ① `app.py`

**全体の司令塔**です。

```text
Trace
 ↓
Parser
 ↓
Normalizer
 ↓
Correlation
 ↓
Incident
 ↓
Hypothesis
 ↓
Laya
 ↓
Result
 ↓
SQLite
```

各モジュールを直接つなぐだけにします。

ここにはトラブル解析ロジックを大量に書かない方針です。

---

# 3. `trace/`

ここは**トレースを事実データに変換する層**です。

### `trace/parser.py`

```text
LOG FILE
 ↓
raw lines
```

担当：

* ファイル読み込み
* encoding処理
* 行番号保持
* 将来的には複数ログ形式対応

例えば、

```text
2026-09-21 10:31:03.025 TaskB TIMEOUT PLC01
```

を読み込みます。

---

### `trace/normalizer.py`

ここが重要です。

異なるログ形式を、

```json
{
  "timestamp": "...",
  "task": "TaskB",
  "event": "TIMEOUT",
  "message": "PLC01"
}
```

のような**共通イベント形式**に変換します。

将来、制御サーバーが10種類のログを出しても、後段は同じ形式で処理できます。

---

### `trace/correlation.py`

イベント同士の関係を作ります。

例えば、

```text
TaskA START
   ↓
MSG_SEND
   ↓
TaskB START
   ↓
PLC_WRITE
   ↓
TIMEOUT
```

を時間・ID・Taskなどで関連付けます。

将来的には、

```text
±10 ms
±100 ms
±1 sec
±10 sec
```

などの時間窓を設定します。

---

# 4. `graph/`

ここは**トレースをグラフとして扱う層**です。

### `graph/event_graph.py`

イベントの順序関係。

```text
E1 → E2 → E3 → E4
```

---

### `graph/task_graph.py`

Task間の関係。

```text
TaskA
  │
  ├── MSG001 → TaskB
  │
  └── MSG002 → TaskC
```

---

### `graph/dependency_graph.py`

ここが将来の本命です。

```text
Function
   ↓
Middleware
   ↓
Message
   ↓
Data
   ↓
Task
```

現在は空のプレースホルダーですが、**既存のtree-sitter解析DBと接続する場所**にします。

---

# 5. `knowledge/`

ここは**制御システムそのものの知識DB**です。

### `knowledge/functions.py`

C関数情報。

将来的には、

```json
{
  "function": "send_plc_command",
  "role": "IO",
  "task": "TaskB",
  "middleware": [
    "middleware_write"
  ]
}
```

などを格納します。

---

### `knowledge/middleware.py`

独自Middlewareの情報。

例えば、

```text
middleware_write()
middleware_read()
middleware_send()
middleware_receive()
```

など。

ここは今回のL2システムでは非常に重要です。

---

### `knowledge/rules.py`

**AIに渡す前の決定論的ルール**です。

例えば、

```text
TIMEOUT
 ↓
PLC_COMMUNICATION
MESSAGE_FLOW
TIMING
```

のように、まず候補を絞ります。

これにより、Layaに無関係な候補まで大量に渡さなくて済みます。

---

# 6. `decision/`

ここが**Jev/Laya型Decision Engineの層**です。

### `decision/laya.py`

Laya専用のAdapterです。

重要なのは、

```text
analysis
   ↓
DecisionEngine
   ↓
Laya
```

という境界を作ること。

将来、

```text
Laya
 ↓
NanoJev
```

に交換しても、上位ロジックを変更しなくて済みます。

---

### `decision/hypotheses.py`

原因仮説を作ります。

例えばTIMEOUTなら、

```text
1. PLC communication failure
2. Message flow delay
3. Timing problem
```

など。

---

### `decision/evaluator.py`

仮説をDecision Engineに渡します。

例えば、

```text
PLC communication
        0.71

Message flow
        0.13

Timing
        0.08
```

のような結果を受け取る場所です。

---

# 7. `analysis/`

ここは**トラブル解析そのもの**です。

### `analysis/incident.py`

大量のトレースから、

> 今回のトラブルは何か？

を決めます。

例えば、

```text
TIMEOUT
ERROR
ALARM
```

など。

---

### `analysis/evidence.py`

原因候補を支持する証拠を集めます。

例えば、

```text
TIMEOUT
 ↓
PLC_WRITE
 ↓
responseなし
 ↓
Task ERROR
```

を、

```text
Evidence
```

としてまとめます。

---

### `analysis/rootcause.py`

最終的な原因候補をまとめる場所です。

将来的には、

```text
Candidate
Probability
Evidence
Contradicting Evidence
Related Function
Related Task
Related Message
```

をまとめます。

---

# 8. `storage/`

SQLite層です。

### `storage/sqlite.py`

DBへのアクセスを集中させます。

### `storage/schema.sql`

最初は、

```text
incidents
```

だけですが、最終的には、

```text
incidents
events
tasks
messages
functions
middleware
hypotheses
evidence
decisions
```

まで拡張できます。

---

# 9. `ui/dashboard.py`

最終的にはここをWeb UIにします。

例えば、

```text
=================================================
 Incident: 20260921-103102
=================================================

TIMEOUT
TaskB
PLC01

Root Cause Candidates

① PLC Communication       71%
② Message Flow            13%
③ Timing                   8%

-------------------------------------------------

Evidence

10:31:02.021 PLC_WRITE
10:31:03.025 TIMEOUT
10:31:03.030 ERROR

-------------------------------------------------

[Trace]
[Task Graph]
[Source Code]
[Middleware]
=================================================
```

という画面を作る想定です。

---

# 10. `tests/`

ここはかなり重要です。

AIを導入するシステムでは、

```text
Parser
Correlation
Graph
```

までを**決定論的にテスト**できるようにしておくべきです。

例えば、

```text
同じtrace
↓
毎回同じEvent Graph
```

である必要があります。

AI部分だけが変動する構造にします。

---

# 11. 今回のMVPで実装済みの範囲

今回のZIPは「空のフォルダ」ではなく、最低限動く骨格にしています。

例えば、

```text
sample_trace.log
```

には、

```text
TaskA REQ_START
TaskA MSG_SEND
TaskB START
TaskB PLC_WRITE
TaskB TIMEOUT
TaskB ERROR
TaskA ABORT
TaskA ALARM
```

というサンプルトレースを入れています。

また、テストも3本用意しています。

---

# 12. 起動方法

展開後、

```powershell
cd C:\Projects\l2-trace-analyzer

py -3.12 -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

python -m pytest
```

まずここまでで、

```text
3 passed
```

になる状態を目標にしています。

その後、

```powershell
python app.py sample_trace.log
```

で解析パイプラインを動かせます。

---

# 13. 次に実装するべき部分

このパッケージでは、あえて**最初から巨大なシステムにしていません**。

次の順番がよいです。

```text
Phase 1
実ログを正しく読む
        ↓
Phase 2
Event Graph
        ↓
Phase 3
Task / Message correlation
        ↓
Phase 4
既存tree-sitter DBとの接続
        ↓
Phase 5
Evidence生成
        ↓
Phase 6
Laya Decision
        ↓
Phase 7
Root Cause UI
        ↓
Phase 8
NanoJevとの交換比較
```

特に**Phase 4を早めに入れる**ことを推奨します。

今回のプロジェクトの価値は、単なるログ解析ではなく、

```text
トレース
  +
Cソース解析
  +
Task
  +
Message
  +
Middleware
  +
Data Flow
  +
Decision Engine
```

を結合するところにあります。

まずこのMVPを実際の環境に置いて、**実際の制御サーバートレースを1件だけ入れて `parser → normalizer → correlation → incident` が正しく動くところまで**作るのが第一段階です。

[1]: https://docs.python.org/3/library/pathlib.html?utm_source=chatgpt.com "pathlib — Object-oriented filesystem paths — Python 3.14.7 documentation"
