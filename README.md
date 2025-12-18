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

## コンフリクトを避けるための上書き用ファイルと手順

GitHub 上で「Resolve conflicts」の画面が出た場合は、下記いずれかの方法で **bundle 内の正規版で全上書き** してください。

1. 画面上で上書きする場合
   - 衝突している各ファイルで `<<<<<<<` から `>>>>>>>` までを **すべて削除** し、下記ファイルを開いて中身を丸ごとコピー＆ペーストします。
   - 貼り付け先とコピー元の対応
     - `bundle/app.py` → `app.py`
     - `bundle/app_utils.py` → `app_utils.py`
     - `bundle/requirements.txt` → `requirements.txt`
     - `bundle/README.md` → `README.md`
     - `bundle/data/arima_sample.csv` → `data/arima_sample.csv`
   - すべて貼り替えたら「Mark as resolved」を押して保存してください。

2. 手元で上書きしてプッシュする場合
   - ルートで以下を実行すると bundle 版で上書きできます。

     ```bash
     ./apply_bundle.sh
     git status  # 差分確認
     git add . && git commit -m "Reset files from bundle" && git push
     ```

どちらの方法でも、bundle 配下の内容をそのまま上書きすれば最新版にリセットできます。
