from pathlib import Path

import pandas as pd
import streamlit as st

from app_utils import (
    DEFAULT_MODEL,
    PredictionRoles,
    build_prediction,
    build_prediction_with_llm,
    build_sign_theory_plan,
    build_sign_theory_plan_with_llm,
    evaluate_single,
    evaluate_single_with_llm,
)


st.set_page_config(page_title="有馬記念AI予想", page_icon="🐎", layout="wide")
st.title("有馬記念 3機能付きAI予想アプリ")
st.caption("Excel/CSVデータを元にLLMが推奨する出力を生成するアプリです。")


DEFAULT_DATA_URL = st.secrets.get(
    "DEFAULT_DATA_URL", "https://raw.githubusercontent.com/owner/repo/main/data/arima_sample.csv"
)
LOCAL_SAMPLE = Path(__file__).parent / "data" / "arima_sample.csv"

api_key = st.secrets.get("OPENAI_API_KEY")
model_name = st.secrets.get("OPENAI_MODEL", DEFAULT_MODEL)
client = None
if api_key:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
    except Exception as exc:  # pragma: no cover - defensive
        st.error(f"OpenAIクライアントの初期化に失敗しました: {exc}")


@st.cache_data(show_spinner=False)
def load_tabular(
    file: st.runtime.uploaded_file_manager.UploadedFile | str | Path,
) -> pd.DataFrame:
    try:
        if isinstance(file, (str, Path)):
            file_str = str(file)
            if file_str.lower().endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        else:
            filename = getattr(file, "name", "").lower()
            if filename.endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
    except Exception as exc:  # pragma: no cover - Streamlit friendly error
        st.error(f"データ読み込みに失敗しました: {exc}")
        return pd.DataFrame()

    if "馬番" in df.columns:
        df["馬番"] = pd.to_numeric(df["馬番"], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_default_data(url: str, fallback: Path) -> pd.DataFrame:
    try:
        df = load_tabular(url)
        if not df.empty:
            st.toast("GitHubのデータを読み込みました")
            return df
    except Exception:
        pass

    if fallback.exists():
        st.toast("GitHub取得に失敗したため、同梱サンプルを使用します")
        return load_tabular(fallback)
    return pd.DataFrame()


def require_data(data: pd.DataFrame) -> bool:
    if data is None:
        st.warning("先にExcel/CSVファイルをアップロードするか、サンプルを読み込んでください。")
        return False
    if data.empty:
        st.warning("データが空です。シートや列名を確認してください。")
        return False
    return True


with st.sidebar:
    st.header("予想用データ")
    uploaded = st.file_uploader("データをアップロード", type=["xlsx", "xls", "csv"])
    use_sample = st.checkbox("GitHubのサンプルデータを使う", value=True)
    st.caption(f"サンプルURL: {DEFAULT_DATA_URL}")
    example_cols = [
        "馬番",
        "馬名",
        "総合評価",
        "近走指数",
        "スピード指数",
        "調教評価",
        "重賞実績",
        "中山実績",
        "芝適性",
        "馬ポテンシャル",
        "騎手評価",
        "騎手勝率",
        "コース適性",
        "中山実績指数",
    ]
    st.markdown(
        "期待する主な列名例: " + ", ".join(example_cols) + "\n(不足していても動きますが、精度は落ちます)"
    )

data = None
data_label = ""
if uploaded:
    data = load_tabular(uploaded)
    data_label = uploaded.name
elif use_sample:
    data = load_default_data(DEFAULT_DATA_URL, LOCAL_SAMPLE)
    data_label = "GitHubサンプル"

if data is not None and not data.empty:
    st.success(f"{data_label} を読み込みました（{len(data)}行）")
    st.dataframe(data.head(10))

if not api_key:
    st.warning(
        "st.secrets['OPENAI_API_KEY'] を設定するとLLMによる推論が有効になります。"
        "現在は簡易スコアによるフォールバック動作です。"
    )
else:
    st.info(f"LLMモード: {model_name}")


tab1, tab2, tab3 = st.tabs(["総合予想", "単体評価", "サイン理論"])


with tab1:
    st.subheader("機能①: 総合予想")
    st.markdown(
        "Startボタンを押すだけで、アップロードしたデータを元に『◎本命〜✕危険馬』と買い目案を提示します。"
    )
    if st.button("総合予想を実行", type="primary"):
        if require_data(data):
            if client:
                picks, buy = build_prediction_with_llm(data, client, model=model_name)
            else:
                picks, buy = build_prediction(data)
            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.markdown("#### 印付き予想")
                for label in PredictionRoles:
                    st.write(picks.get(label, f"{label}: データ不足"))
            with col_right:
                st.markdown("#### 推奨買い方")
                st.write(buy)


with tab2:
    st.subheader("機能②: 単体評価")
    st.markdown("馬番を入力すると、馬・騎手・コースを個別分析し統合評価を返します。")
    target_number = st.number_input("馬番を入力", min_value=1, max_value=20, value=1, step=1)
    if st.button("この馬を評価する", type="primary"):
        if require_data(data):
            if client:
                evaluation = evaluate_single_with_llm(data, int(target_number), client, model=model_name)
            else:
                evaluation = evaluate_single(data, int(target_number))
            st.markdown(f"### 馬番 {target_number} の評価")
            st.metric("総合評価", f"{evaluation.overall_score} 点")
            st.markdown("#### 馬評価")
            st.write(evaluation.horse_comment)
            st.markdown("#### 人（騎手）評価")
            st.write(evaluation.jockey_comment)
            st.markdown("#### コース評価")
            st.write(evaluation.course_comment)
            st.markdown("#### 総合評価まとめ")
            st.info(evaluation.summary)


with tab3:
    st.subheader("機能③: サイン理論")
    st.markdown("2025年の出来事からサイン数字を抽出し、買い目案を提示するモックです。")
    if st.button("サイン理論で提案", type="primary"):
        if client:
            steps, plan = build_sign_theory_plan_with_llm(client, model=model_name)
        else:
            steps, plan = build_sign_theory_plan()
        st.markdown("#### 今年の出来事 & 抽出数字")
        st.write("\n".join(steps))
        st.markdown("#### 買い方プラン")
        st.write(plan)


st.markdown(
    "---\nStreamlit CloudのSecretsに OPENAI_API_KEY / OPENAI_MODEL / DEFAULT_DATA_URL を設定すると、"
    "LLM推論とGitHub上のデータ参照が自動で有効になります。"
)
