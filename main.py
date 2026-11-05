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
    df = pd.read_csv(DATA_URL, encoding="utf-8")

    transactions = []
    all_items = set()

    for menu_str in df["메뉴"].dropna():
        if not isinstance(menu_str, str):
            continue
        # 세로줄(|)로 분리
        items = menu_str.split("|")
        cleaned_items = set()
        for item in items:
            # 괄호 및 괄호 안의 내용 제거 후 공백 정리
            cleaned = re.sub(r"\(.*?\)", "", item).strip()
            if cleaned:
                cleaned_items.add(cleaned)
                all_items.add(cleaned)
        if cleaned_items:
            transactions.append(cleaned_items)

    total_transactions = len(transactions)

    # 1개 아이템 빈도 계산
    item_counts = {}
    for t in transactions:
        for item in t:
            item_counts[item] = item_counts.get(item, 0) + 1

    # 아이템 쌍(2개 아이템) 빈도 및 연관 규칙 계산
    pair_counts = {}
    for t in transactions:
        for item1, item2 in combinations(sorted(t), 2):
            pair_counts[(item1, item2)] = pair_counts.get((item1, item2), 0) + 1

    rules = []
    for (item1, item2), pair_freq in pair_counts.items():
        # item1 -> item2
        sup_A = item_counts[item1] / total_transactions
        sup_B = item_counts[item2] / total_transactions
        sup_AB = pair_freq / total_transactions

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

        # item2 -> item1 (조건과 결과를 바꾼 규칙)
        conf_2to1 = pair_freq / item_counts[item2]
        lift_2to1 = conf_2to1 / sup_A

        rules.append(
            {
                "조건": item2,
                "결과": item1,
                "동시": pair_freq,
                "지지도": round(sup_AB, 4),
                "신뢰도": round(conf_2to1, 4),
                "향상도": round(lift_2to1, 4),
            }
        )

    rules_df = pd.DataFrame(rules)
    unique_pairs_count = len(pair_counts)

    return (
        rules_df,
        total_transactions,
        len(all_items),
        unique_pairs_count,
        sorted(list(all_items)),
        item_counts,
        pair_counts,
    )


(
    rules_df,
    total_days,
    num_menu_types,
    num_pairs,
    menu_list,
    item_counts,
    pair_counts,
) = load_and_process_data()

st.title("🍱 송탄고 급식 규칙 찾기")

# 상단 한 줄 요약 정보 표시
st.write(
    f"**급식 일수:** {total_days}일 | **메뉴 종류 수:** {num_menu_types}개 | **함께 나온 적이 있는 메뉴 쌍의 수:** {num_pairs}쌍"
)
st.divider()

# 사이드바 컨트롤러
st.sidebar.header("필터 및 정렬 설정")

selected_menu = st.sidebar.selectbox(
    "특정 메뉴 선택 (전체 보기: 선택 안 함)", options=["전체 보기"] + menu_list
)

min_co_occurrence = st.sidebar.slider(
    "최소 동시 일수 설정", min_value=1, max_value=10, value=1
)

sort_option = st.sidebar.radio(
    "정렬 기준 선택", options=["향상도 순", "신뢰도 순", "동시 순"]
)

# 데이터 필터링
filtered_df = rules_df.copy()

# 1. 메뉴 필터링
if selected_menu != "전체 보기":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu)
        | (filtered_df["결과"] == selected_menu)
    ]

# 2. 최소 동시 일수 필터링
filtered_df = filtered_df[filtered_df["동시"] >= min_co_occurrence]

# 데이터 정렬
if sort_option == "향상도 순":
    filtered_df = filtered_df.sort_values(
        by=["향상도", "신뢰도", "동시"], ascending=[False, False, False]
    )
elif sort_option == "신뢰도 순":
    filtered_df = filtered_df.sort_values(
        by=["신뢰도", "향상도", "동시"], ascending=[False, False, False]
    )
else:
    filtered_df = filtered_df.sort_values(
        by=["동시", "향상도", "신뢰도"], ascending=[False, False, False]
    )

filtered_df = filtered_df.reset_index(drop=True)

# 남은 규칙 개수 안내
st.info(
    f"📌 최소 동시 일수 **{min_co_occurrence}일 이상** 조건 적용 후 **남은 규칙 개수:** 총 **{len(filtered_df)}개**"
)

# Plotly 가로 막대그래프 (향상도 상위 10개)
st.subheader("📊 향상도 상위 10개 규칙")
top10_df = filtered_df.nlargest(10, "향상도").copy()

if not top10_df.empty:
    top10_df["규칙"] = top10_df["조건"] + " ➔ " + top10_df["결과"]
    top10_df = top10_df.sort_values(by="향상도", ascending=True)

    fig = px.bar(
        top10_df,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        title="향상도(Lift) Top 10 규칙",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        yaxis_title="연관 규칙 (조건 ➔ 결과)",
        xaxis_title="향상도",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("선택한 조건에 해당하는 규칙이 없습니다.")

# 규칙 표 출력
st.subheader("📋 급식 연관 규칙 표")
st.dataframe(filtered_df, use_container_width=True)

st.divider()

# 함께 나온 적 없는 짝 섹션
st.subheader("❌ 함께 나온 적 없는 짝")

target_menu = st.selectbox(
    "조회할 메뉴를 선택하세요 (독립 분석용):",
    options=menu_list,
    key="never_paired_menu_select",
)

if target_menu:
    target_count = item_counts.get(target_menu, 0)
    st.markdown(
        f"**선택한 메뉴 [{target_menu}] 가 나온 날 수:** **{target_count}일**"
    )

    never_paired = []
    for other_menu, count in item_counts.items():
        if other_menu == target_menu:
            continue
        # 둘이 함께 나온 일수 (pair_counts 검색)
        pair_key1 = (min(target_menu, other_menu), max(target_menu, other_menu))
        co_occurred_days = pair_counts.get(pair_key1, 0)

        # 한 번도 같이 나오지 않았고(&) 혼자서는 10일 이상 나온 메뉴
        if co_occurred_days == 0 and count >= 10:
            never_paired.append({"메뉴": other_menu, "혼자 나온 날 수": count})

    if never_paired:
        never_paired_df = pd.DataFrame(never_paired).sort_values(
            by="혼자 나온 날 수", ascending=False
        )
        never_paired_df = never_paired_df.reset_index(drop=True)
        st.write(
            f"**[{target_menu}]** 와 한 번도 함께 나온 적 없으면서 10일 이상 나온 메뉴 목록 (나온 날이 많은 순):"
        )
        st.dataframe(never_paired_df, use_container_width=True)
    else:
        st.info(
            f"**[{target_menu}]** 와 한 번도 함께 나오지 않으면서 10일 이상 나온 메뉴가 없습니다."
        )
