確認しました。結論から言うと、**Laya Python版は Windows + CPU + RAM 16GB で動かせる構成です**。しかも、NanoJevと違って、公式READMEにCPU実測値が記載されています。([GitHub][1])

ただし、**Python 3.13ではなくPython 3.12を使う**ことを推奨します。

## 結論

| 項目                         | 判定                          |
| -------------------------- | --------------------------- |
| Windows                    | **○**                       |
| CPUのみ                      | **○**                       |
| RAM 16GB                   | **○**                       |
| Python                     | **○**                       |
| Python 3.12                | **推奨**                      |
| Python 3.13                | △ 今回は避ける                    |
| GPU                        | 不要                          |
| PyTorch                    | 必要                          |
| Hugging Face               | モデル初回取得に必要                  |
| オフライン推論                    | **○** モデル取得後                |
| 日本語                        | `laya-multilingual` を使うのが適切 |
| Jev型 Choice / Score / Noul | **○**                       |

Layaは421MパラメータのModernBERT版、322Mパラメータのmultilingual版などを提供しています。READMEにはCPUでの実測として、`Router(preload=True)` が **193–464 ms/request** と記載されています。つまり、CPU推論は単なる理論上の可能性ではなく、実際に測定されています。([GitHub][1])

---

# 1. 16GB RAMなら問題ないか

問題ありません。

ただし、**3モデル全部を常駐させる必要はありません**。

LayaのREADMEでは、

> 3モデル合計 約1.16B parameters / 約4.6GB fp32

とされています。デフォルトでは1モデルだけを常駐させ、必要に応じて入れ替える設計です。([GitHub][2])

今回の目的なら、

```text
Windows
│
├─ Python 3.12
├─ PyTorch CPU
├─ Laya
│
└─ laya-multilingual
      ↓
    約322M parameters
```

くらいから始めるのが適切です。

---

# 2. Python 3.12を推奨する理由

現在のPyPIには `laya 0.3.3`/`0.3.4` が公開されています。パッケージ自体はPython 3.8以上として登録されています。([PyPI][3])

ただし、今回の目的では **Python 3.12を使うのが安全**です。

特にLayaはPyTorch + Transformers系なので、

```text
Python 3.12
  ↓
PyTorch CPU
  ↓
Transformers
  ↓
ModernBERT/mmBERT
  ↓
Laya
```

という既知のML環境に寄せます。

現在お使いのNanoJevのPython 3.13環境とは**完全に分離**してください。

---

# 3. インストール

まずPython 3.12が入っているか確認。

```powershell
py -0p
```

例えば、

```text
 -V:3.13
 -V:3.12
```

となればOKです。

なければPython 3.12を別途インストールしてください。

---

## プロジェクト作成

今回はNanoJevとは分けます。

```powershell
mkdir C:\Projects\Laya
cd C:\Projects\Laya
```

仮想環境を作ります。

```powershell
py -3.12 -m venv .venv
```

有効化。

```powershell
.\.venv\Scripts\Activate.ps1
```

確認。

```powershell
python --version
```

期待値：

```text
Python 3.12.x
```

---

# 4. まずCPU版PyTorchを入れる

ここが重要です。

今回の目的は**GPUを一切使わない**ことなので、CPU版PyTorchを明示して入れます。

```powershell
python -m pip install --upgrade pip
```

続いてCPU版：

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

確認：

```powershell
python -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available())"
```

必ず、

```text
cuda: False
```

になることを確認します。

---

# 5. Layaをインストール

その後、

```powershell
pip install laya
```

公式のインストール方法も `pip install laya` です。([GitHub][1])

確認：

```powershell
python -c "import laya; print(laya)"
```

エラーが出なければ第一段階成功です。

---

# 6. 最初はRouterを使わない

ここは重要です。

Layaには、

```python
Router()
```

がありますが、最初の実験では使わない方がよいです。

まず**multilingualモデルを直接ロード**します。

日本語を扱うので、

```text
convaiinnovations/laya
```

ではなく、

```text
convaiinnovations/laya
subfolder="multilingual"
```

を使います。

READMEでもmultilingual版は100以上の言語を対象としています。([GitHub][1])

---

# 7. 最初の動作確認

`test_laya.py` を作ります。

```python
import laya

print("Loading Laya...")

agent = laya.load(
    "convaiinnovations/laya",
    subfolder="multilingual"
)

print("Model loaded.")

state = {
    "text": "この関数はPLCから取得したデータを解析して制御値を計算する"
}

questions = {
    "role": {
        "type": "choice",
        "instructions": "この関数の主な役割は何ですか？",
        "criteria": {
            "CONTROL": "制御処理",
            "CALC": "計算処理",
            "IO": "入出力処理",
            "MESSAGE": "メッセージ処理",
            "UTILITY": "汎用処理"
        }
    },
    "is_control": {
        "type": "noul",
        "instructions": "この関数は制御処理を行っていますか？"
    }
}

result = agent.predict(state, questions)

print(result)
```

実行：

```powershell
python test_laya.py
```

---

# 8. ここで確認したいもの

例えば概念的には、

```text
answers:
  role:
    choice: CALC
    probabilities:
      CONTROL: ...
      CALC: ...
      IO: ...
      MESSAGE: ...
      UTILITY: ...

  is_control:
    noul: ...
```

という結果が返ってきます。

これが出れば、今回の研究目的としてはかなり重要なところまで到達です。

つまり、

```text
普通のLLM
   ↓
文章を生成
   ↓
人間が解釈
```

ではなく、

```text
Laya
   ↓
状態
   +
Decision Question
   ↓
Choice / Noul / Score
   ↓
確率 + confidence
```

という**Jev型Decision Engine**を実際に触れます。

Laya公式も `choice`、`score`、`noul` をDecision Primitiveとして明示しています。([PyPI][3])

---

# 9. 注意：Layaは「日本語なら必ず高精度」ではない

ここはL2用途では重要です。

Layaの公開ベンチマークでは、multilingualモデルは多数言語を扱えますが、**Layaはゼロショットの汎用Decision Engineとして万能ではありません**。公式自身も、typed-decisionsについてベースモデルはゼロショットでは弱く、専門用途にはfine-tuningが重要だと説明しています。([PyPI][3])

したがって、最初から

> 「LayaならL2ソースコードを正確に分類できる」

とは考えません。

今回の目的はむしろ、

```text
① Jev/LayaのDecision構造を理解
        ↓
② CPUで実際に動かす
        ↓
③ L2の小さな分類問題を与える
        ↓
④ confidenceがどう使えるか確認
        ↓
⑤ Qwen3-8Bとの役割分担を考える
```

です。

---

# 10. あなたのL2用途なら、この実験が面白い

例えば10～20個程度の実際のC関数について、

```text
質問1:
この関数の主目的は？

CONTROL
CALCULATION
IO
MESSAGE
MONITOR
UTILITY
UNKNOWN
```

さらに、

```text
質問2:
この関数は制御タスクの主要処理に属するか？

YES / NO
```

さらに、

```text
質問3:
この関数を変更した場合、他タスクへの影響度は？

NONE
LOW
MEDIUM
HIGH
CRITICAL
```

とします。

すると、

```text
                Laya
                  │
        ┌─────────┼─────────┐
        ↓         ↓         ↓
      Choice     Noul      Score
        │         │         │
     役割分類   Yes/No     影響度
```

という形になります。

これは、以前検討していた

```text
tree-sitter
    ↓
関数・呼出し・データアクセス
    ↓
Decision
    ↓
L2構造理解
```

に非常に素直に接続できます。

---

## まずここまでで十分です

**最初からRouter、APIサーバー、L2連携まで作らない**方がよいです。

まず、

```powershell
C:\Projects\Laya
└─ .venv
```

を作って、

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install laya
```

↓

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

↓

```text
False
```

↓

`test_laya.py`

↓

**Choice / Noul / Scoreが返ることを確認**

という順番にしましょう。

なお、Layaは2026年9月にかなり活発に更新されており、現在のGitHubにはOpenAI互換REST APIやCPU/GPU関連の変更も進んでいます。そのため、今回は**固定バージョンで環境を作るより、まず現行PyPI版をクリーンなPython 3.12環境で動かす**のがよいです。([GitHub][4])

[1]: https://github.com/NandhaKishorM/laya/blob/main/README.md "laya/README.md at main · NandhaKishorM/laya · GitHub"
[2]: https://github.com/NandhaKishorM/laya/blob/main/README.md?utm_source=chatgpt.com "laya/README.md at main · NandhaKishorM/laya · GitHub"
[3]: https://pypi.org/project/laya/ "laya · PyPI"
[4]: https://github.com/NandhaKishorM/laya/issues?utm_source=chatgpt.com "Issues · NandhaKishorM/laya · GitHub"




原因は明確です。**Laya本体ではなく、Windows上のHugging Face Hubキャッシュのシンボリックリンク問題**です。

ログを見ると、モデルのダウンロード自体はかなり進んでいます。

```text
638MB / 678MB
↓
653MB
↓
WinError 1314
```

そして失敗箇所は、

```text
os.symlink(...)
OSError: [WinError 1314]
```

です。

Hugging Face公式でも、WindowsではDeveloper Modeを有効にするか管理者権限で実行しないとキャッシュのsymlinkを作れない場合がある、と説明されています。([Hugging Face][1])

## 一番簡単な解決方法

今回は**Developer Modeを変更せず、Hugging Faceのsymlinkを無効化**しましょう。

PowerShellで、Layaのvenvを有効にした状態で：

```powershell
$env:HF_HUB_DISABLE_SYMLINKS="1"
```

そのまま、

```powershell
python test_laya.py
```

を再実行してください。

Hugging Faceには `HF_HUB_DISABLE_SYMLINKS=1` があり、これを設定するとsymlinkを使わず、ファイルを通常のコピーとして保存します。Windowsの非Developer Mode環境向けの公式な回避方法です。([GitHub][2])

### 毎回設定したくない場合

ユーザー環境変数に設定できます。

```powershell
[Environment]::SetEnvironmentVariable(
    "HF_HUB_DISABLE_SYMLINKS",
    "1",
    "User"
)
```

PowerShellを一度閉じて開き直してください。

---

## ただし、今回もう一つ重要な点があります

前回の私のテストコードでは、

```python
laya.load(
    "convaiinnovations/laya",
    subfolder="multilingual"
)
```

としていました。

現在のLaya READMEを見ると、multilingualモデルは独立した

```text
convaiinnovations/laya-multilingual
```

としても公開されています。また、Layaには現在、

* `english` — 421M
* `multilingual` — 322M
* `typed-decisions` — 421M

の3チェックポイントがあります。([GitHub][3])

**今回の目的はJev型Decisionの理解なので、最初は `typed-decisions` を試す方が適切です。**

ただし、日本語を入力するので、ここは少し注意が必要です。`typed-decisions` はModernBERT-largeベースで、multilingual版は100以上の言語対応ですが、Laya READMEではtyped-decisionsは特定の4つのtyped-decision workflow向けにfine-tuneされたモデルとされています。([GitHub][3])

したがって、まず**モデルを正常にロードできることを確認するだけ**なら、現在のスクリプトを変更せずに、

```powershell
$env:HF_HUB_DISABLE_SYMLINKS="1"
python test_laya.py
```

で進めるのが最短です。

---

## ダウンロード済みの678MBはどうなる？

今回の失敗でキャッシュが中途半端になっている可能性があります。

まず、

```powershell
Get-ChildItem "$env:USERPROFILE\.cache\huggingface\hub\models--convaiinnovations--laya" -Recurse -File |
    Measure-Object -Property Length -Sum
```

を実行してください。

もし大量のファイルが残っていれば、そのまま再実行して**再利用される可能性があります**。

なお、symlinkを無効にすると同じモデルのファイルがコピーされるため、ディスク使用量は増える可能性があります。Hugging Faceもこの点を明記しています。([GitHub][2])

---

### 次にやること

まずこれだけ実行してください。

```powershell
$env:HF_HUB_DISABLE_SYMLINKS="1"
python test_laya.py
```

**ここでモデルロードまで進むか確認しましょう。**

次に出るエラーがあれば、そのまま貼ってください。今回はダウンロード段階なので、**CPU推論そのものが動くかどうかはまだ未確認**です。そこまで一つずつ切り分けます。

[1]: https://huggingface.co/docs/huggingface_hub/installation?utm_source=chatgpt.com "Installation · Hugging Face"
[2]: https://github.com/huggingface/huggingface_hub/blob/main/docs/source/en/package_reference/environment_variables.md?utm_source=chatgpt.com "huggingface_hub/docs/source/en/package_reference/environment_variables.md at main · huggingface/huggingface_hub · GitHub"
[3]: https://github.com/NandhaKishorM/laya/blob/main/laya/router.py?utm_source=chatgpt.com "laya/laya/router.py at main · NandhaKishorM/laya · GitHub"




テスト結果
成功です。**Laya Python版が Windows + CPU + 16GB RAM 環境で実際に推論まで動作しました。**

今回の結果は、単なるモデルロードではなく、**Choice と Noul のDecisionをCPU上で実行できた**ことを確認できています。

## 1. 今回確認できたこと

```text
Model loaded.
```

に続いて、

```text
role
  choice = CALC
```

と、

```text
is_control
  noul = 0.9314
```

が返っています。

つまり、

```text
Windows
  ↓
Python 3.12
  ↓
Laya
  ↓
CPU
  ↓
Laya model
  ↓
Decision
```

が成立しています。

**NanoJevで問題になったCUDA必須問題はありません。**

---

# 2. この結果がJev理解にかなり重要

今回の入力は、

> この関数はPLCから取得したデータを解析して制御値を計算する

でした。

Layaはこれに対して、

### Choice

```text
CONTROL    0.3526
CALC       0.4771
IO         0.0268
MESSAGE    0.0762
UTILITY    0.0674
```

から、

```text
CALC
```

を選択しました。

重要なのは単に「CALC」と答えたことではありません。

**候補ごとの確率分布を返している**ことです。

---

# 3. `confidence` の意味

ここがJev型Decisionで非常に重要です。

```text
choice: CALC
confidence: 0.2572
```

です。

一見、

> CALC 47.71%だから自信がある

ように見えますが、そうではありません。

候補間の差が小さいため、

```text
CONTROL  35.26%
CALC     47.71%
```

であり、**CALCに圧倒的に集中しているわけではありません**。

つまり、

```text
CALC
confidence = 0.2572
```

は、

> CALCを選んだが、判断にはかなり曖昧さがある

という状態として扱えます。

これはL2の保守支援に非常に使いやすい考え方です。

---

# 4. 一方、Noulはかなり明確

こちら：

```text
is_control
noul = 0.9314
confidence = 0.9314
```

はかなり違います。

質問は、

```text
この関数は制御処理を行っていますか？
```

でした。

Layaは、

```text
YES ≈ 93.14%
```

という判断をしています。

したがって、

```text
Noul
  ↓
0.9314
```

を使って、

```text
>= 0.90
    ↓
自動採用

0.70～0.90
    ↓
追加確認

< 0.70
    ↓
人間確認
```

のような**Decision Workflow**を構築できます。

※この閾値は現時点では例であり、実際のL2データで校正する必要があります。

---

# 5. これが普通のLLMとの違い

Qwen3-8Bなどの一般的なLLMなら、

```text
質問
 ↓
「この関数は計算処理を担当している可能性が高いです。」
```

という**文章**を返します。

Layaでは、

```json
{
  "choice": "CALC",
  "probabilities": {
    "CONTROL": 0.3526,
    "CALC": 0.4771,
    "IO": 0.0268,
    "MESSAGE": 0.0762,
    "UTILITY": 0.0674
  },
  "confidence": 0.2572
}
```

という**機械がそのまま利用できるDecision**になります。

ここが今回理解したかったJev型アーキテクチャの核心部分です。

---

# 6. L2に置き換えると面白い

あなたのL2解析システムなら、例えば、

```text
Cソース
   │
   ↓
tree-sitter
   │
   ├─ function
   ├─ calls
   ├─ middleware_calls
   ├─ data_accesses
   └─ message_edges
          │
          ↓
       Laya
          │
    ┌─────┼─────┐
    ↓     ↓     ↓
  Choice Noul  Score
    │     │     │
    ↓     ↓     ↓
 役割   判定   影響度
```

という構成にできます。

例えば、

### Choice

```text
この関数の主要な役割は？

CONTROL
CALC
IO
MESSAGE
MONITOR
UTILITY
```

### Noul

```text
この関数は制御タスクの主要処理か？
```

### Score

```text
この関数の変更が他タスクへ波及する可能性は？
```

という3種類に分けられます。

---

# 7. 次は「同じ質問をQwen3-8Bにも投げる」

ここからが非常に面白い比較になります。

現在の環境にはすでにQwen3-8Bがありますので、

```text
同じC関数
       │
       ├── Qwen3-8B
       │      ↓
       │    自然言語回答
       │
       └── Laya
              ↓
          Choice/Noul/Score
              ↓
          probability
```

を比較できます。

これによって、

> **「Jev/Layaを使うと、普通のLLMを使う場合と何が変わるのか？」**

を感覚ではなく実験で確認できます。

---

## 次の実験をおすすめします

まず、**LayaのChoice / Noul / Scoreを10問程度の固定テストで試す**のがよいです。

例えば：

| ID  | L2判定                          |
| --- | ----------------------------- |
| F01 | CONTROL / CALC / IO / MESSAGE |
| F02 | CONTROL / CALC / IO / MESSAGE |
| F03 | CONTROL / CALC / IO / MESSAGE |
| …   | …                             |
| F10 | CONTROL / CALC / IO / MESSAGE |

そして、

```text
Laya
├─ choice
├─ probability
├─ confidence
└─ inference time
```

をCSVに保存します。

その後、**Qwen3-8Bにも同じ10問を与え、結果を比較**します。

この段階まで行けば、次に「LayaをL2開発・保守システムのどこに組み込むべきか」をかなり具体的に設計できます。
