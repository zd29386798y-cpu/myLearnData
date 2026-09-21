はい。まずは**「NanoJevを実際に起動して、入力 → Decision → 確率分布」を確認できるところまで**進めましょう。

ただし、先に1点重要です。

### 現在のNanoJevの公式手順

現在のGitHub版では、NanoJevは

* Qwen3-0.6BをバックボーンにしたDecision Model
* Choice / Boolean / Score
* 複数のstate/questionをまとめて処理
* 推論結果を確率分布として返す
* 永続的な推論サービスとして起動可能

という構成です。([GitHub][1])

一方、**公式の推論手順はCUDA環境を前提にしています**。したがって、今の「CPUのみ・RAM 16GB」という条件では、まず**学習や大規模推論をするのではなく、CPUでどこまで動くかを確認する実験**として進めるのがよいです。公式runbookにもPython 3.11+とCUDA環境が記載されています。([GitHub][2])

---

# Step 1：まず環境を分離する

既存のQwen3-8B環境を壊さないように、

```text
C:\Projects\
    ├─ tree-sitter-Project
    ├─ study-ai-home
    ├─ ...
    └─ NanoJev
```

とします。

PowerShellで、

```powershell
cd C:\Projects

git clone https://github.com/TianyuCodings/NanoJev.git

cd NanoJev

python -m venv .venv

.\.venv\Scripts\Activate.ps1
```

NanoJev公式READMEでもGit clone → Python環境 → `requirements-toy.txt`という流れになっています。([GitHub][3])

---

# Step 2：Pythonバージョン確認

```powershell
python --version
```

NanoJevの公式runbookでは **Python 3.11以上**です。([GitHub][2])

以前使われていたPython 3.13.11でも条件上は問題ありません。

次に、

```powershell
python -m pip --version
```

---

# Step 3：依存パッケージ

まず、

```powershell
python -m pip install -r requirements-toy.txt
```

です。

ここではまだモデルをダウンロードしません。

インストールが終わったら、

```powershell
python -m pip list
```

で確認します。

---

# Step 4：最初は「モデル推論」よりWebデモを確認

NanoJevには、実際のモデル推論とは別に、記録済みのMaze/SnakeのDecisionをブラウザで見る仕組みがあります。

公式手順は、

```powershell
python -m http.server 8080 --bind 127.0.0.1 --directory web
```

そして、

```text
http://127.0.0.1:8080/side-by-side.html
```

です。([GitHub][3])

これは**NanoJevをインストールした意味を確認するための最初のチェックポイント**として便利です。

ただし、これは録画済みの結果を見るだけなので、

> 「自分の入力をNanoJevに与えたらどういう確率が返るのか？」

はまだ確認できません。

---

# Step 5：本命「NanoJevサーバー」を起動する

公式のモデル取得方法はHugging Faceからcheckpointを取得します。

```python
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="C-Tianyu/NanoJev",
    local_dir="checkpoints/NanoJev",
    allow_patterns=[
        "best.safetensors",
        "config.json",
        "tokenizer/*",
        "backbone_config/*"
    ],
)
```

公式READMEにこの手順があります。([GitHub][3])

その後、

```powershell
python scripts/serve_decisions.py `
    --checkpoint-dir checkpoints/NanoJev `
    --web-root web `
    --port 8765
```

です。

正常に動けば、

```text
http://127.0.0.1:8765
```

にアクセスできます。

APIは、

```text
POST /api/evaluate
```

です。([GitHub][3])

---

# ただし、ここでCPU-only問題が出る可能性があります

ここは慎重に進めたいです。

公式READMEは、

> Prepare a CUDA environment

としており、現在のNanoJevは**CPU-only運用を公式サポートしているとは読み取れません**。([GitHub][3])

なので、あなたの環境では、

```text
NanoJev
   │
   ├── Pythonインストール       ← まず確認
   │
   ├── checkpoint取得            ← 次
   │
   ├── serve_decisions.py        ← CPUで起動できるか
   │
   └── /api/evaluate             ← 実際のDecision
```

の順に**一段ずつ確認**しましょう。

最初からCUDA向けの設定を無理に変更する必要はありません。

---

# Step 6：最初に確認したいDecision

NanoJevが動いたら、最初はL2とは関係ない簡単な入力にします。

例えば、

```text
State:

A temperature sensor reports 850 degrees.
The control system has a limit of 800 degrees.
```

質問：

```text
Is the temperature above the limit?
```

Booleanなら、

```text
YES
NO
```

ではなく、NanoJevのBoolean形式で

```text
probability = 0.xx
```

が返ってくることを確認します。

---

# Step 7：次にChoice

次はこれです。

```text
State:

A function reads a temperature,
calculates a correction value,
and writes the corrected value to a control variable.
```

Question:

```text
What is the primary role of this function?
```

Candidates:

```text
initialization
control
calculation
monitoring
communication
```

理想的には、

```json
{
  "control": 0.XX,
  "calculation": 0.XX,
  "monitoring": 0.XX,
  "communication": 0.XX,
  "initialization": 0.XX
}
```

のような**全候補の確率分布**を見る。

これがJev型Decisionを理解するうえで非常に重要です。

NanoJevはChoiceについて、2～255候補を動的に与えられ、候補ごとの確率分布を返す設計です。([GitHub][1])

---

# Step 8：最後にL2の小さな問題

ここまで確認できたら、初めてL2の実データを1～10件程度入れます。

例えば、

```text
Function:
FOCS_Start

Calls:
  SendMessage(MSG_START)
  ReadData()
  SetControlValue()

Data:
  furnace_status
  target_temperature
```

Question:

```text
What is the primary role of this function?
```

Candidates:

```text
initialization
control
monitoring
communication
calculation
```

そして、

```text
NanoJev
    ↓
probabilities
    ↓
人間が確認
```

とします。

**この段階では自動的にL2の分類DBを書き換えない**方がよいです。

まず、

```text
NanoJevの判断
      ↓
人間の判断
      ↓
一致？
```

を記録します。

---

# 最初のゴール

私は今回、ここまでを**第1マイルストーン**にすることを勧めます。

```text
[1] NanoJev GitHub取得
        ↓
[2] Python環境構築
        ↓
[3] requirements導入
        ↓
[4] Webデモ確認
        ↓
[5] checkpoint取得
        ↓
[6] serve_decisions.py
        ↓
[7] CPUで起動できるか確認
        ↓
[8] /api/evaluate
        ↓
[9] Boolean
        ↓
[10] Choice
        ↓
[11] Score
        ↓
[12] L2サンプル10件
```

ここまで来れば、

> **「Jevとはこういうものなのか」**

を実際に触って理解できます。

その後に初めて、

```text
NanoJev
   VS
Qwen3-0.6B
   VS
Qwen3-4B
   VS
Qwen3-8B
```

を比較すればよいです。

---

## まず今やること

あなたのPCがWindowsなら、**PowerShellで以下だけ実行してください。**

```powershell
cd C:\Projects
git clone https://github.com/TianyuCodings/NanoJev.git
cd NanoJev
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install -r requirements-toy.txt
```

ここまで実行して、**エラーが出たらそのまま全文を貼ってください。**

特に今回はCPU-onlyなので、**CUDAを勝手に追加したり、依存パッケージを適当に変更したりせず、公式構成からどこまで動くかを確認しながら進める**のがよいです。公式リポジトリは現在も更新されており、最近の版では推論サーバーや統合checkpointも追加されています。([GitHub][4])

[1]: https://github.com/tianyucodings/nanojev?utm_source=chatgpt.com "GitHub - TianyuCodings/NanoJev: A nano replica of Jev: parallel decisions, dynamic candidates, and an end-to-end training pipeline. · GitHub"
[2]: https://github.com/TianyuCodings/NanoJev/blob/main/research/pipeline_runbook.md?utm_source=chatgpt.com "NanoJev/research/pipeline_runbook.md at main · TianyuCodings/NanoJev · GitHub"
[3]: https://github.com/TianyuCodings/NanoJev/blob/main/README.md?utm_source=chatgpt.com "NanoJev/README.md at main · TianyuCodings/NanoJev · GitHub"
[4]: https://github.com/TianyuCodings/NanoJev?utm_source=chatgpt.com "GitHub - TianyuCodings/NanoJev: A nano replica of Jev: parallel decisions, dynamic candidates, and an end-to-end training pipeline. · GitHub"
