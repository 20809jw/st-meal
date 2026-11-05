import re
from itertools import combinations
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="송탄고 급식 연관 규칙 분석", layout="wide")

# 1. 데이터 로드 및 전처리
DATA_URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"


@st.cache_data
def load_and_process_data():
    try:
        raw_df = pd.read_csv(DATA_URL, encoding="utf-8")
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame(), 0, 0, 0, [], {}, {}

    transactions = []
    all_items = set()

    # CSV의 각 행(하루 식단) 단위로 처리
    for _, row in raw_df.iterrows():
        menu_str = str(row["메뉴"]) if pd.notna(row["메뉴"]) else ""
        if not menu_str or menu_str.strip() == "":
            continue

        # 세로줄(|) 또는 줄바꿈(\n)으로 분리
        items = re.split(r"[|\n]", menu_str)
        cleaned_items = set()

        for item in items:
            # 괄호 및 괄호 안의 내용 제거 (예: 쌀밥(고) -> 쌀밥)
            cleaned = re.sub(r"\(.*?\)", "", item).strip()
            if cleaned:
                cleaned_items.add(cleaned)
                all_items.add(cleaned)

        if cleaned_items:
            transactions.append(cleaned_items)

    total_transactions = len(transactions)
    if total_transactions == 0:
        return pd.DataFrame(), 0, 0, 0, [], {}, {}

    # 1개 아이템 출현 일수(빈도) 계산
    item_counts = {}
    for t in transactions:
        for item in t:
            item_counts[item] = item_counts.get(item, 0) + 1

    # 아이템 쌍(2개 아이템) 동시 출현 일수 계산
    pair_counts = {}
    for t in transactions:
        for item1, item2 in combinations(sorted(t), 2):
            pair_counts[(item1, item2)] = pair_counts.get((item1, item2), 0) + 1

    # 연관 규칙 계산
    rules = []
    for (item1, item2), pair_freq in pair_counts.items():
        sup_A = item_counts[item1] / total_transactions
        sup_B = item_counts[item2] / total_transactions
        sup_AB = pair_freq / total_transactions

        # item1 -> item2
        conf_1to2 = pair_freq / item_counts[item1]
        lift_1to2 = conf_1to2 / sup_B

        rules.append(
            {
                "조건": item1,
                "결과": item2,
                "동시": pair_freq,
                "지지도": round(sup_AB, 4),
                "신뢰도": round(conf_1to2, 4),
                "향상도": round(lift_1to2, 4),
            }
        )

        # item2 -> item1
        conf_2to1 = pair_freq / item_counts[item2]
        lift_2to
