import streamlit as st
import pandas as pd

from app_utils import PredictionRoles, build_prediction, build_sign_theory_plan, evaluate_single


st.set_page_config(page_title="有馬記念AI予想", page_icon="🐎", layout="wide")
st.title("有馬記念 3機能付きAI予想アプリ")
st.caption("Excelデータを元にLLMが推奨する出力を模したモックアプリです。")


@st.cache_data(show_spinner=False)
def load_excel(file: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
    df = pd.read_excel(file)
    if "馬番" in df.columns:
        df["馬番"] = pd.to_numeric(df["馬番"], errors="coerce")
    return df


def require_data(data: pd.DataFrame) -> bool:
    if data is None:
        st.warning("先にExcelファイルをアップロードしてください。")
        return False
    if data.empty:
        st.warning("データが空です。シートや列名を確認してください。")
        return False
    return True


with st.sidebar:
    st.header("予想用データ")
    uploaded = st.file_uploader("Excelをアップロード", type=["xlsx", "xls"])
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

if uploaded:
    data = load_excel(uploaded)
    st.success(f"{uploaded.name} を読み込みました（{len(data)}行）")
    st.dataframe(data.head(10))
else:
    data = None


tab1, tab2, tab3 = st.tabs(["総合予想", "単体評価", "サイン理論"])


with tab1:
    st.subheader("機能①: 総合予想")
    st.markdown(
        "Startボタンを押すだけで、アップロードしたデータを元に『◎本命〜✕危険馬』と買い目案を提示します。"
    )
    if st.button("総合予想を実行", type="primary"):
        if require_data(data):
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
            evaluation = evaluate_single(data, int(target_number))
            st.markdown(f"### 馬番 {target_number} の評価")
            st.metric("総合評価", f"{evaluation.overall_score} 点")
            st.write("馬評価", evaluation.horse_comment)
            st.write("騎手評価", evaluation.jockey_comment)
            st.write("コース評価", evaluation.course_comment)
            st.info(evaluation.summary)


with tab3:
    st.subheader("機能③: サイン理論")
    st.markdown("2025年の出来事からサイン数字を抽出し、買い目案を提示するモックです。")
    if st.button("サイン理論で提案", type="primary"):
        steps, plan = build_sign_theory_plan()
        st.markdown("#### 今年の出来事 & 抽出数字")
        st.write("\n".join(steps))
        st.markdown("#### 買い方プラン")
        st.write(plan)


st.markdown(
    "---\nこのアプリはLLMに渡すためのプロンプトや入力データの形を固めるためのモックです。\n"
    "実運用ではAPIキーやプロンプトを組み込んで応答を置き換えてください。"
)
