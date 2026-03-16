"""
data_loader.py — 统一数据读取模块

职责：读取 clean_distribution_growth_analysis.csv，处理字段类型，
      提供带筛选的数据接口。
"""
from __future__ import annotations
import os
import pandas as pd
import streamlit as st

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "clean_distribution_growth_analysis.csv")


@st.cache_data(ttl=300, show_spinner=False)
def load_data() -> pd.DataFrame:
    """读取并预处理完整数据集。

    Returns:
        pd.DataFrame: 完整分析数据集，event_date 为 datetime 类型。
    """
    df = pd.read_csv(DATA_PATH, parse_dates=["event_date"])
    # 统一字段类型
    str_cols = ["user_id","user_type","age_group","gender","city_tier",
                "item_id","item_category","price_band","content_type",
                "channel","experiment_group","strategy_type"]
    for c in str_cols:
        df[c] = df[c].astype(str).str.strip()
    int_cols = ["impression","click","detail_view","add_to_cart","order","pay","is_new_payer"]
    for c in int_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    float_cols = ["pay_amount","campaign_cost"]
    for c in float_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df


def get_filter_options(df: pd.DataFrame) -> dict:
    """获取各筛选字段的候选值列表。

    Args:
        df: 完整数据集

    Returns:
        dict: {字段名: 排序后的唯一值列表}
    """
    return {
        "channel":          sorted(df["channel"].unique().tolist()),
        "user_type":        sorted(df["user_type"].unique().tolist()),
        "content_type":     sorted(df["content_type"].unique().tolist()),
        "item_category":    sorted(df["item_category"].unique().tolist()),
        "price_band":       sorted(df["price_band"].unique().tolist()),
        "experiment_group": sorted(df["experiment_group"].unique().tolist()),
        "age_group":        sorted(df["age_group"].unique().tolist()),
        "gender":           sorted(df["gender"].unique().tolist()),
        "city_tier":        sorted(df["city_tier"].unique().tolist()),
    }


def load_filtered_data(filters: dict) -> pd.DataFrame:
    """读取并应用筛选条件的数据。

    Args:
        filters: {字段名: 值或值列表或(start, end)元组}

    Returns:
        pd.DataFrame: 筛选后的数据集
    """
    from modules.filter_utils import apply_common_filters
    df = load_data()
    return apply_common_filters(df, filters)
