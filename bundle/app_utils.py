"""Utility functions for the Arima Kinen prediction Streamlit app."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
from openai import OpenAI


@dataclass
class HorseEvaluation:
    number: int
    horse_score: float
    jockey_score: float
    course_score: float
    overall_score: float
    horse_comment: str
    jockey_comment: str
    course_comment: str
    summary: str


PredictionRoles = ["◎本命", "○対抗", "▲単穴", "☆穴馬", "✕危険馬"]

DEFAULT_MODEL = "gpt-4o-mini"


def _safe_numeric(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _compute_base_score(row: pd.Series) -> float:
    core_features = [
        _safe_numeric(row.get("総合評価", 0.0)),
        _safe_numeric(row.get("近走指数", 0.0)),
        _safe_numeric(row.get("スピード指数", 0.0)),
        _safe_numeric(row.get("調教評価", 0.0)) * 0.5,
    ]
    score = sum(core_features)
    bonus_flags = ["重賞実績", "中山実績", "芝適性"]
    for flag in bonus_flags:
        if str(row.get(flag, "")).strip() in {"◎", "○", "▲", "A", "B"}:
            score += 1.5
    return score


def _format_dataframe_for_prompt(df: pd.DataFrame, max_rows: int = 20) -> str:
    """Return a trimmed CSV-style string for inclusion in prompts."""
    display_cols = [
        col
        for col in [
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
        if col in df.columns
    ]
    trimmed = df[display_cols].head(max_rows) if display_cols else df.head(max_rows)
    return trimmed.to_csv(index=False)


def _call_llm(
    client: OpenAI,
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.4,
) -> str:
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content or ""


def build_prediction(df: pd.DataFrame) -> Tuple[Dict[str, str], str]:
    if df.empty:
        return {}, "データが空です。Excelを読み込んでください。"

    scored = df.copy()
    scored["_score"] = scored.apply(_compute_base_score, axis=1)
    if "馬番" in scored.columns:
        scored = scored.sort_values(["_score", "馬番"], ascending=[False, True])
    else:
        scored = scored.sort_values(["_score"], ascending=False)

    picks: Dict[str, str] = {}
    for label, (_, row) in zip(PredictionRoles, scored.head(len(PredictionRoles)).iterrows()):
        number = row.get("馬番", "?")
        name = row.get("馬名", "不明")
        picks[label] = f"{label}: {name} (馬番 {number})"

    top_numbers: Iterable[str] = [str(row.get("馬番", "?")) for _, row in scored.head(3).iterrows()]
    buy_message = (
        "三連複フォーメーション例: 1列目 {0}, 2列目 {1}, 3列目 {2}〜人気薄を網羅。".format(
            "・".join(top_numbers[:1]), "・".join(top_numbers[:2]), "・".join(top_numbers)
        )
    )
    return picks, buy_message


def build_prediction_with_llm(
    df: pd.DataFrame, client: OpenAI, model: str = DEFAULT_MODEL
) -> Tuple[Dict[str, str], str]:
    if df.empty:
        return {}, "データが空です。Excelを読み込んでください。"

    table_text = _format_dataframe_for_prompt(df)
    system_prompt = (
        "あなたは有馬記念の予想専門家です。入力された表を根拠に、"
        "◎本命、○対抗、▲単穴、☆穴馬、✕危険馬と推奨の買い方を日本語で出力してください。"
        "出力は必ずJSON形式で、keysを ['◎本命','○対抗','▲単穴','☆穴馬','✕危険馬','buy_plan'] としてください。"
    )
    user_prompt = (
        "以下の出走データを参考に予想をしてください。各印には馬番と理由を付けてください。\n"
        f"データ:\n{table_text}"
    )
    content = _call_llm(client, system_prompt, user_prompt, model=model)
    picks: Dict[str, str] = {}
    buy_message = ""
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            for label in PredictionRoles:
                value = parsed.get(label)
                if isinstance(value, str):
                    picks[label] = value
            buy_message = parsed.get("buy_plan", "")
    except json.JSONDecodeError:
        buy_message = "JSON解析に失敗しましたが、テキストとして利用してください。\n" + content

    return picks, buy_message or "フォーメーション例を生成できませんでした。"


def _extract_target_row(df: pd.DataFrame, number: int) -> Optional[pd.Series]:
    if "馬番" not in df.columns:
        return None
    match = df[df["馬番"] == number]
    if match.empty:
        return None
    return match.iloc[0]


def evaluate_single(df: pd.DataFrame, number: int) -> HorseEvaluation:
    row = _extract_target_row(df, number)
    if row is None:
        return HorseEvaluation(
            number=number,
            horse_score=0.0,
            jockey_score=0.0,
            course_score=0.0,
            overall_score=0.0,
            horse_comment="対象の馬番がデータに存在しません。",
            jockey_comment="",
            course_comment="",
            summary="データを確認してください。",
        )

    horse_score = _safe_numeric(row.get("馬ポテンシャル", row.get("馬力指数", 0.0))) + _safe_numeric(row.get("調教評価", 0.0))
    jockey_score = _safe_numeric(row.get("騎手評価", 0.0)) + _safe_numeric(row.get("騎手勝率", 0.0))
    course_score = _safe_numeric(row.get("中山実績指数", row.get("コース適性", 0.0)))
    overall_score = round(horse_score * 0.5 + jockey_score * 0.3 + course_score * 0.2, 2)

    horse_comment = (
        f"馬ポテンシャル: {_safe_numeric(row.get('馬ポテンシャル', 'N/A'))} / 調教評価: {_safe_numeric(row.get('調教評価', 'N/A'))}。"
    )
    jockey_comment = (
        f"騎手評価: {_safe_numeric(row.get('騎手評価', 'N/A'))} / 勝率: {_safe_numeric(row.get('騎手勝率', 'N/A'))}%。"
    )
    course_comment = (
        f"コース適性: {_safe_numeric(row.get('コース適性', 'N/A'))} / 中山実績: {_safe_numeric(row.get('中山実績指数', 'N/A'))}。"
    )
    summary = (
        f"総合評価 {overall_score} 点。馬の完成度を軸に、騎手の安定感と中山適性を加味したバランス型の評価です。"
    )

    return HorseEvaluation(
        number=number,
        horse_score=round(horse_score, 2),
        jockey_score=round(jockey_score, 2),
        course_score=round(course_score, 2),
        overall_score=overall_score,
        horse_comment=horse_comment,
        jockey_comment=jockey_comment,
        course_comment=course_comment,
        summary=summary,
    )


def evaluate_single_with_llm(
    df: pd.DataFrame, number: int, client: OpenAI, model: str = DEFAULT_MODEL
) -> HorseEvaluation:
    row = _extract_target_row(df, number)
    if row is None:
        return HorseEvaluation(
            number=number,
            horse_score=0.0,
            jockey_score=0.0,
            course_score=0.0,
            overall_score=0.0,
            horse_comment="対象の馬番がデータに存在しません。",
            jockey_comment="",
            course_comment="",
            summary="データを確認してください。",
        )

    system_prompt = (
        "あなたは競馬データアナリストです。入力される行データを読み、"
        "STEP1 馬評価、STEP2 騎手評価、STEP3 コース評価、STEP4 総合評価を順に考察してください。"
        "日本語で簡潔に説明し、JSONで出力してください。"
        "JSON keys: horse_comment, jockey_comment, course_comment, summary, overall_score。overall_scoreは0-100点の数値で。"
    )
    row_text = row.to_json(force_ascii=False)
    user_prompt = f"対象馬番 {number} のデータ: {row_text}"
    content = _call_llm(client, system_prompt, user_prompt, model=model)

    horse_comment = ""
    jockey_comment = ""
    course_comment = ""
    summary = ""
    overall_score = 0.0
    try:
        parsed = json.loads(content)
        horse_comment = str(parsed.get("horse_comment", ""))
        jockey_comment = str(parsed.get("jockey_comment", ""))
        course_comment = str(parsed.get("course_comment", ""))
        summary = str(parsed.get("summary", ""))
        overall_score = float(parsed.get("overall_score", 0.0))
    except json.JSONDecodeError:
        summary = "JSON解析に失敗しました。テキスト出力を参照してください。"
        horse_comment = content

    return HorseEvaluation(
        number=number,
        horse_score=_safe_numeric(row.get("馬ポテンシャル", 0.0)),
        jockey_score=_safe_numeric(row.get("騎手評価", 0.0)),
        course_score=_safe_numeric(row.get("コース適性", row.get("中山実績指数", 0.0))),
        overall_score=round(overall_score, 2),
        horse_comment=horse_comment,
        jockey_comment=jockey_comment,
        course_comment=course_comment,
        summary=summary,
    )


def build_sign_theory_plan(events: Optional[List[Tuple[str, List[int]]]] = None) -> Tuple[List[str], str]:
    default_events: List[Tuple[str, List[int]]] = [
        ("阪神淡路大震災から30年", [1, 7, 30]),
        ("エリザベス女王生誕99周年からの節目", [9, 9, 12]),
        ("阪神優勝関連の数字", [6, 18]),
        ("東京オリンピック開催から4年", [2, 4, 20]),
    ]
    event_list = events or default_events

    highlighted_numbers: List[int] = []
    steps: List[str] = []
    for title, numbers in event_list:
        steps.append(f"・{title}: {', '.join(map(str, numbers))} が浮上")
        highlighted_numbers.extend(numbers)

    unique_numbers = sorted({n for n in highlighted_numbers if 1 <= n <= 18})
    pairings = [f"{a}-{b}" for a in unique_numbers for b in unique_numbers if a < b][:10]
    plan = "サイン有力数字: " + ", ".join(map(str, unique_numbers))
    plan += "\n買い目案 (ワイド/三連複): " + ", ".join(pairings)
    return steps, plan


def build_sign_theory_plan_with_llm(client: OpenAI, model: str = DEFAULT_MODEL) -> Tuple[List[str], str]:
    system_prompt = (
        "あなたはサイン理論の専門家です。2025年の出来事や話題から数字を抽出し、"
        "有馬記念の買い目に使える数字セットとフォーメーション案を提案してください。"
        "JSON形式で、events(文字列リスト)とplan(文字列)を返してください。"
    )
    user_prompt = (
        "2025年に起きた出来事や予定を3-5個挙げ、それぞれに関連する数字を示し、"
        "そこから導かれる買い目案をまとめてください。"
    )
    content = _call_llm(client, system_prompt, user_prompt, model=model, temperature=0.6)
    steps: List[str] = []
    plan = ""
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            raw_events = parsed.get("events") or []
            if isinstance(raw_events, list):
                steps = [str(e) for e in raw_events]
            plan = str(parsed.get("plan", ""))
    except json.JSONDecodeError:
        steps = ["JSON解析に失敗しました。テキストを参照してください。", content]
    return steps, plan or "買い目案を生成できませんでした。"
