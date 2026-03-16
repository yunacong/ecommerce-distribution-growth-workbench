"""
filter_utils.py — 统一筛选逻辑模块

职责：处理页面筛选条件，避免各页面重复写筛选逻辑。
"""
from __future__ import annotations
import pandas as pd
from datetime import datetime


def apply_common_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """统一应用筛选条件到 DataFrame。

    Args:
        df: 原始数据集
        filters: 筛选条件字典，支持以下格式：
            - date_range: (start_date, end_date) 元组
            - 其他字段: 单个值（str）或值列表（list）

    Returns:
        pd.DataFrame: 筛选后的数据副本
    """
    result = df.copy()

    for key, value in filters.items():
        if value is None:
            continue

        # 日期范围筛选
        if key == "date_range":
            start, end = value
            if start is not None:
                result = result[result["event_date"] >= pd.Timestamp(start)]
            if end is not None:
                result = result[result["event_date"] <= pd.Timestamp(end)]
            continue

        # 字段不存在则跳过
        if key not in result.columns:
            continue

        # 空列表 = 不筛选
        if isinstance(value, list):
            if len(value) == 0:
                continue
            result = result[result[key].isin(value)]
        elif isinstance(value, str):
            if value.lower() in ("all", "全部", ""):
                continue
            result = result[result[key] == value]

    return result.reset_index(drop=True)


def build_filters_from_sidebar(
    df: pd.DataFrame,
    show_experiment: bool = False,
    date_default_days: int = 30,
) -> dict:
    """在 Streamlit 侧边栏构建通用筛选组件，返回 filters 字典。

    Args:
        df: 完整数据集（用于获取候选值）
        show_experiment: 是否显示实验组筛选
        date_default_days: 默认日期范围（天数）

    Returns:
        dict: 筛选条件字典
    """
    import streamlit as st
    from modules.data_loader import get_filter_options

    opts = get_filter_options(df)
    filters: dict = {}

    # 日期范围
    min_date = df["event_date"].min().date()
    max_date = df["event_date"].max().date()
    default_start = max_date - pd.Timedelta(days=date_default_days - 1)
    default_start = max(default_start.date() if hasattr(default_start, "date") else default_start, min_date)

    date_range = st.sidebar.date_input(
        "📅 日期范围",
        value=(default_start, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        filters["date_range"] = (date_range[0], date_range[1])
    elif isinstance(date_range, (list, tuple)) and len(date_range) == 1:
        filters["date_range"] = (date_range[0], max_date)

    # 流量场景
    channel_opts = opts["channel"]
    selected_channels = st.sidebar.multiselect(
        "📡 流量场景 (Channel)", channel_opts, default=[]
    )
    if selected_channels:
        filters["channel"] = selected_channels

    # 用户类型
    user_opts = opts["user_type"]
    selected_users = st.sidebar.multiselect(
        "👤 用户类型 (User Type)", user_opts, default=[]
    )
    if selected_users:
        filters["user_type"] = selected_users

    # 内容类型
    content_opts = opts["content_type"]
    selected_content = st.sidebar.multiselect(
        "🎬 内容类型 (Content Type)", content_opts, default=[]
    )
    if selected_content:
        filters["content_type"] = selected_content

    # 商品类目
    cat_opts = opts["item_category"]
    selected_cats = st.sidebar.multiselect(
        "🛍️ 商品类目 (Category)", cat_opts, default=[]
    )
    if selected_cats:
        filters["item_category"] = selected_cats

    # 实验组
    if show_experiment:
        exp_opts = opts["experiment_group"]
        selected_exp = st.sidebar.multiselect(
            "🧪 实验组别 (Experiment Group)", exp_opts, default=[]
        )
        if selected_exp:
            filters["experiment_group"] = selected_exp

    return filters
