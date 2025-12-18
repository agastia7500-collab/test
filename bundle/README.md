# 有馬記念 AI 予想モックアプリ

Streamlit で動く有馬記念の予想 UI です。以下の 3 機能を備えています。

1. **総合予想**: アップロードした Excel の指標をもとに「◎本命〜✕危険馬」を自動提示。
2. **単体評価**: 馬番を指定して馬・騎手・コースの評価と総合点を表示。
3. **サイン理論**: 2025 年の出来事から派生するサイン数字と買い目案を生成。

LLM 連携は OpenAI API を利用しています。Streamlit Cloud の Secrets に API キーを登録すると、アップロードした Excel/CSV を読み込み、LLM で予想とサイン理論を生成します。

## セットアップと実行

```bash
pip install -r requirements.txt  # 依存が未インストールの場合
streamlit run app.py
```

### Secrets の設定例 (Streamlit Cloud)

`.streamlit/secrets.toml` または Cloud の Secrets に以下を設定してください。

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"  # 任意、未設定なら gpt-4o-mini を使用
DEFAULT_DATA_URL = "https://raw.githubusercontent.com/<owner>/<repo>/main/data/arima_sample.csv"
```

`DEFAULT_DATA_URL` には GitHub に置いた Excel/CSV の RAW URL を指定します。取得に失敗した場合は、レポジトリ同梱の `data/arima_sample.csv` をフォールバックとして読み込みます。

## データの前提

Excel には最低限 `馬番`、`馬名` の列があるとスムーズです。評価精度を高めるために以下の列の追加を推奨します。

- 総合評価, 近走指数, スピード指数, 調教評価
- 重賞実績, 中山実績, 芝適性
- 馬ポテンシャル, 騎手評価, 騎手勝率, コース適性, 中山実績指数

列名が不足していても動作しますが、スコアリングの精度が下がります。

## コンフリクトを避けるための上書き用ファイル

Git のコンフリクトが発生した場合は、`bundle/` 配下に現在の正規版ファイルを複製しています。必要に応じて以下をルートに上書きコピーしてください。

- `bundle/app.py` → `app.py`
- `bundle/app_utils.py` → `app_utils.py`
- `bundle/requirements.txt` → `requirements.txt`
- `bundle/README.md` → `README.md`
- `bundle/data/arima_sample.csv` → `data/arima_sample.csv`

これらをそのまま上書きすれば、最新版にリセットできます。
