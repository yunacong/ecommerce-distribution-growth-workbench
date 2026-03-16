"""
metric_calculator.py — 指标计算模块

职责：计算 CTR / CVR / GMV / ROI 等核心指标及分组聚合结果。
所有指标口径集中维护在此模块，页面文件不得散写计算逻辑。
"""
from __future__ import annotations
import pandas as pd
import numpy as np


# ── 基础口径常量 ───────────────────────────────────────────────────────────────
FUNNEL_STEPS = ["impression", "click", "detail_view", "add_to_cart", "order", "pay"]
FUNNEL_LABELS = {
    "impression":   "曝光 (Impression)",
    "click":        "点击 (Click)",
    "detail_view":  "详情浏览 (Detail View)",
    "add_to_cart":  "加购 (Add to Cart)",
    "order":        "下单 (Order)",
    "pay":          "支付 (Pay)",
}


def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法，分母为0时返回 default。"""
    return numerator / denominator if denominator > 0 else default


def calc_core_metrics(df: pd.DataFrame) -> dict:
    """计算核心指标汇总（用于指标卡片展示）。

    Args:
        df: 筛选后的数据集

    Returns:
        dict: {
            "ctr": float, "cvr": float, "gmv": float,
            "new_user_rate": float, "roi": float,
            "impression": int, "click": int, "pay": int
        }
    """
    if df.empty:
        return {k: 0.0 for k in ["ctr","cvr","gmv","new_user_rate","roi",
                                  "impression","click","pay"]}

    total_imp   = df["impression"].sum()
    total_click = df["click"].sum()
    total_pay   = df["pay"].sum()
    total_gmv   = df["pay_amount"].sum()
    total_cost  = df["campaign_cost"].sum()
    total_new   = df["is_new_payer"].sum()

    return {
        "ctr":           _safe_div(total_click, total_imp),
        "cvr":           _safe_div(total_pay,   total_click),
        "gmv":           total_gmv,
        "new_user_rate": _safe_div(total_new,   total_pay),
        "roi":           _safe_div(total_gmv,   total_cost),
        "impression":    int(total_imp),
        "click":         int(total_click),
        "pay":           int(total_pay),
    }


def calc_trend_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """按日期聚合计算趋势指标。

    Args:
        df: 筛选后的数据集

    Returns:
        pd.DataFrame: 含 event_date / ctr / cvr / gmv / roi 列，按日期升序
    """
    if df.empty:
        return pd.DataFrame(columns=["event_date","ctr","cvr","gmv","roi"])

    grp = df.groupby("event_date").agg(
        impression   = ("impression",    "sum"),
        click        = ("click",         "sum"),
        pay          = ("pay",           "sum"),
        pay_amount   = ("pay_amount",    "sum"),
        campaign_cost= ("campaign_cost", "sum"),
        is_new_payer = ("is_new_payer",  "sum"),
    ).reset_index()

    grp["ctr"] = grp.apply(lambda r: _safe_div(r["click"],       r["impression"]),   axis=1)
    grp["cvr"] = grp.apply(lambda r: _safe_div(r["pay"],         r["click"]),        axis=1)
    grp["gmv"] = grp["pay_amount"]
    grp["roi"] = grp.apply(lambda r: _safe_div(r["pay_amount"],  r["campaign_cost"]), axis=1)
    grp["new_user_rate"] = grp.apply(lambda r: _safe_div(r["is_new_payer"], r["pay"]), axis=1)

    return grp.sort_values("event_date").reset_index(drop=True)


def calc_group_metrics(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """按指定分组维度聚合计算指标。

    Args:
        df: 筛选后的数据集
        group_cols: 分组字段列表，如 ["channel"] 或 ["user_type"]

    Returns:
        pd.DataFrame: 含 ctr / cvr / gmv / roi / detail_view_rate /
                      add_to_cart_rate / order_rate / pay_rate 等列
    """
    if df.empty:
        return pd.DataFrame()

    grp = df.groupby(group_cols).agg(
        impression    = ("impression",    "sum"),
        click         = ("click",         "sum"),
        detail_view   = ("detail_view",   "sum"),
        add_to_cart   = ("add_to_cart",   "sum"),
        order         = ("order",         "sum"),
        pay           = ("pay",           "sum"),
        pay_amount    = ("pay_amount",    "sum"),
        campaign_cost = ("campaign_cost", "sum"),
        is_new_payer  = ("is_new_payer",  "sum"),
    ).reset_index()

    grp["ctr"]              = grp.apply(lambda r: _safe_div(r["click"],       r["impression"]),   axis=1)
    grp["cvr"]              = grp.apply(lambda r: _safe_div(r["pay"],         r["click"]),        axis=1)
    grp["detail_view_rate"] = grp.apply(lambda r: _safe_div(r["detail_view"], r["click"]),        axis=1)
    grp["add_to_cart_rate"] = grp.apply(lambda r: _safe_div(r["add_to_cart"], r["detail_view"]), axis=1)
    grp["order_rate"]       = grp.apply(lambda r: _safe_div(r["order"],       r["add_to_cart"]), axis=1)
    grp["pay_rate"]         = grp.apply(lambda r: _safe_div(r["pay"],         r["order"]),       axis=1)
    grp["gmv"]              = grp["pay_amount"]
    grp["roi"]              = grp.apply(lambda r: _safe_div(r["pay_amount"],  r["campaign_cost"]), axis=1)
    grp["new_user_rate"]    = grp.apply(lambda r: _safe_div(r["is_new_payer"], r["pay"]),          axis=1)

    return grp


def calc_period_comparison(df: pd.DataFrame, current_filters: dict, days: int = 14) -> dict:
    """计算当前周期 vs 上一周期的环比。

    Args:
        df: 完整数据集（未筛选）
        current_filters: 当前筛选条件（含 date_range）
        days: 对比周期天数

    Returns:
        dict: {指标: {"current": float, "previous": float, "change_pct": float}}
    """
    from modules.filter_utils import apply_common_filters

    date_range = current_filters.get("date_range")
    if not date_range:
        return {}

    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    period_len = (end - start).days + 1
    prev_end   = start - pd.Timedelta(days=1)
    prev_start = prev_end - pd.Timedelta(days=period_len - 1)

    other_filters = {k: v for k, v in current_filters.items() if k != "date_range"}
    prev_filters  = {"date_range": (prev_start, prev_end), **other_filters}

    cur_df  = apply_common_filters(df, current_filters)
    prev_df = apply_common_filters(df, prev_filters)

    cur_m  = calc_core_metrics(cur_df)
    prev_m = calc_core_metrics(prev_df)

    result = {}
    for key in ["ctr", "cvr", "gmv", "roi", "new_user_rate"]:
        cur_val  = cur_m.get(key, 0)
        prev_val = prev_m.get(key, 0)
        chg = _safe_div(cur_val - prev_val, prev_val) if prev_val != 0 else 0
        result[key] = {"current": cur_val, "previous": prev_val, "change_pct": chg}

    return result
