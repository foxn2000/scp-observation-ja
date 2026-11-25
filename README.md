# SCP 観測日誌ベンチマーク（scp-observation-ja）

## 概要

本リポジトリ（`foxn2000/scp-observation-ja`）は、SCP 観測日誌ベンチマーク（識別子 `scp-observation-ja`）の評価環境である。評価環境は `verifiers` 0.2.0 の v1 API で実装している。このベンチマークは、SCP 財団 Wiki 日本語版の記事の抜粋にある異常性の規則を架空の観測日誌へ当てはめ、指定時刻の状態を答える日本語の課題からなる。問題文は「この抜粋だけを異常性の根拠として」答えるよう指示しており、記事の知識そのものではなく、抜粋に書かれた規則の読解と長い日誌における状態の追跡を測る。

収録する問題は 100 問である。各問の異常性の規則を JSON 形式の仕様に書き下し、その仕様から日誌を生成した。正解は共通のインタプリタで計算しており、大規模言語モデルに答えさせていない。書かれていない解釈の違いで答えが変わる問は除き、各規則の根拠が抜粋の中にあることを確かめた。その後、盲検の再導出と全件の監査を経て、欠陥とされた問を除いた。被験モデルの正誤を見て問を選んではおらず、問題の作成パイプラインは公開しない。

パッケージ名は `scp-observation-ja`、モジュール名は `scp_observation_ja` である。データセット本体は Hugging Face の `DataPilot/scp-observation-ja` で公開している。評価結果は同データセットの README に記載している。本リポジトリの主なファイル構成を以下に示す。

```text
LICENSE                              CC BY-SA 4.0 の全文
ATTRIBUTION.md                       38 記事の出典
pyproject.toml
scp_observation_ja/__init__.py
scp_observation_ja/taskset.py        タスクの読み込み、採点の登録（verifiers v1）
scp_observation_ja/grading.py        解答の採点
scp_observation_ja/data/tasks.jsonl  100 問
tests/                               pytest のテスト（62 件）
```

## 問の形

収録した 100 問は、SCP 財団 Wiki 日本語版の 38 記事から作成した。内訳は、日本語版の創作記事 23 記事から 61 問、翻訳記事 15 記事から 39 問である。評価時はモデルに問題文を 1 件の `user` メッセージとして渡し、ツールを使わない 1 ターンの対話で解答を得る。

問題文は【指示】、【取り決め】、【資料の抜粋】、【観測日誌】、【設問】、【解答の書き方】の 6 節で構成する。長さは約 1,800〜5,200 字である。【取り決め】には作品固有の取り決めと 09:00 の初期状態を含み、【資料の抜粋】の末尾には出典の行を置く。日誌に登場する個体は、1 問あたり 6〜10 個の記号（甲、乙、丙など）で表す。設問は 3 欄からなり、各欄の時刻と条件に該当する記号をすべて答える。解答は最終行に `解答: ` と記し、3 欄を設問の順に `/` で区切って記号を続けて書く。欄内は順不同であり、該当がない欄は `なし` とする（例：`解答: なし/丁/丁己`）。

1 問目（`scp-374-jp-X3_mid-4000`）の【設問】と【解答の書き方】を以下に示す。この問の正解は `解答: なし/丁/丁己` である。

```text
【設問】
第1欄　09:01の「意識を取り戻した場面まで照会済みの対象者」
第2欄　09:05の「意識を取り戻した場面まで照会済みの対象者」
第3欄　09:09の「意識を取り戻した場面まで照会済みの対象者」
各欄とも該当する記号をすべて答えてください。

【解答の書き方】
最終行に「解答: 」と書き、3個の欄を設問の順に / で区切ってください。各欄には該当する記号を続けて書いてください。欄内は順不同です。該当なしは「なし」と書いてください。
```

各問には難しさの設定を表す `level` を割り当てている。表 1 に、`level` ごとの問数、日誌の事象数（実測）、個体数、照会の時刻を示す。

| `level` | 問数 | 日誌の事象数（実測） | 個体数 | 照会の時刻 |
|---|---:|---|---|---|
| `X1_long` | 31 | 30〜37 | 6〜9 | 3 つ。最後の欄は日誌の最後の時刻 |
| `X6_long_mid` | 30 | 30〜41 | 6〜9 | 3 つ。日誌の途中の時刻も問う |
| `X3_mid` | 23 | 11〜16 | 6 | 3 つ。日誌の途中の時刻も問う |
| `X7_xlong` | 16 | 46〜51 | 8〜10 | 3 つ。日誌の途中の時刻も問う |

## インストールと実行

上記の 100 問を手元で実行するには、Python 3.11〜3.13 と `uv` が必要である。本パッケージをインストールすると、依存する `verifiers` 0.2.0 の評価コマンド `eval` も入る。

```bash
git clone https://github.com/foxn2000/scp-observation-ja.git
cd scp-observation-ja
uv venv
uv pip install .
```

OpenRouter 経由でモデルを評価する例を以下に示す。API キーは環境変数 `OPENROUTER_API_KEY` に設定する。`eval` は既定で評価結果を Prime Intellect のプラットフォームへ送るため、手元だけに残す場合は `--no-push` を付ける。

```bash
.venv/bin/eval scp-observation-ja \
  -m openai/gpt-oss-20b \
  --client.base-url https://openrouter.ai/api/v1 --client.api-key-var OPENROUTER_API_KEY \
  --no-push -o outputs/gpt-oss-20b
```

Python から問題を読み込み、モデルの応答を採点する例を以下に示す。

```python
from scp_observation_ja import ScpObservationTaskset
from scp_observation_ja.taskset import ScpObservationConfig
from scp_observation_ja.grading import score_answer

tasks = ScpObservationTaskset(ScpObservationConfig(id="scp-observation-ja", levels=["X1_long"])).load()
record = tasks[0].data.record  # prompt、fields、symbols、gold などを持つ
result = score_answer(reply, field_count=len(record["fields"]), symbols=record["symbols"], gold=record["gold"])
# result: {"correct": ..., "field_accuracy": ..., "format_error": ..., "field_matches": [...]}
```

同梱の `pytest` テスト（62 件）の実行とパッケージのビルドには、以下のコマンドを使う。

```bash
uv run --with pytest pytest -q
uv build
```

## タスクセットの引数

評価の実行時に対象の問題を変更または絞り込むため、タスクセットは次の引数を `eval` の `--taskset.<名前>` 形式で受け付ける。

- `data_path`（`--taskset.data-path`）：同梱の `data/tasks.jsonl` の代わりに読み込む JSONL ファイルのパス。
- `levels`（`--taskset.levels`）：`level` で対象を絞り込む指定（例：`--taskset.levels X1_long X6_long_mid`）。
- `origins`（`--taskset.origins`）：`jp`（日本語版の創作記事）または `translation`（翻訳記事）で対象を絞り込む指定。
- `max_tasks`（`--taskset.max-tasks`）：絞り込みと `idx` 順の整列の後、先頭から件数を制限する指定。

## 採点

評価で得たモデルの応答は、`scp_observation_ja/grading.py` が次の手順で解析して採点する。

1. 応答を行に分け、各行を NFKC で正規化する。前後の空白と、行全体を囲む Markdown の装飾（`**`、`*`、`__`、`` ` ``）を除いたうえで、`解答:` で始まる最後の行を採点対象とする。その後に説明が続いてもよく、全角の `：` と `／` も受け付ける。
2. `解答:` の後を `/` で分ける。各欄の前後の空白と末尾の `。` を除き、記号の集合または空集合を表す `なし` として読み取る。記号の間には空白、`、`、`,`、`・` を使える。
3. `解答:` の行がない、欄の数が違う、空欄、未知の文字、記号の重複、`なし` と記号の混在のいずれかに該当する場合は、形式不備とする。

解析結果から、以下の報酬と指標を算出する。API エラーなどで応答を取得できなかった試行は採点対象から除外する。

- `correct`（報酬）：形式が正しく、3 欄すべての記号の集合が正解と一致したとき `1.0`、それ以外は `0.0`。
- `format_error`：形式不備のときに `1.0` となる指標。
- `field_accuracy`：一致した欄の割合。
- `field_1_correct`〜`field_3_correct`：第 1 欄から第 3 欄までの各欄の正誤。

## ライセンス

このベンチマーク（問題、データ、評価環境のコード）は CC BY-SA 4.0 で公開する。全文は `LICENSE` にある。ライセンスの扱いは SCP 財団（SCP コミュニティ）のライセンスに準じる。参照先は SCP 財団 Wiki 日本語版のライセンスガイド（https://scp-jp.wikidot.com/licensing-guide）である。

問題文の抜粋の原文は SCP 財団 Wiki 日本語版の記事であり、CC BY-SA 3.0 で公開されている。抜粋と架空の日誌を組み合わせた問題文は、その二次的著作物として CC BY-SA 4.0 で公開する。CC BY-SA 3.0 の作品の二次的著作物に CC BY-SA 4.0 を付けられることは、上記のライセンスガイドの注にも書かれている。出典（記事名、著者または日本語版の投稿者、URL、ライセンス）は、`ATTRIBUTION.md` と各問の【資料の抜粋】の末尾にある出典の行に記載している。Hugging Face データセットの `sources` 列には、記事名、URL、原文のライセンス、日本語版の創作記事の著者を収録している。翻訳記事の日本語版の投稿者は `sources` 列になく、`ATTRIBUTION.md` と出典の行にある。

このベンチマークを再配布または改変するときは、出典の表示と同じライセンスでの公開（継承）が必要である。このベンチマークは SCP 財団 Wiki の公式のものではなく、SCP 財団 Wiki やその著者による支持を受けたものでもない。
