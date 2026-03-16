"""
funnel_analyzer.py — 漏斗分析与异常定位模块

职责：计算漏斗各环节转化率，判断前/后链路问题，输出策略建议。
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from modules.metric_calculator import _safe_div, FUNNEL_STEPS, FUNNEL_LABELS


def build_funnel_summary(df: pd.DataFrame) -> dict:
    """计算全局漏斗汇总。

    Args:
        df: 筛选后的数据集

    Returns:
        dict: {
            "steps": list[str],        # 环节名称
            "labels": list[str],       # 环节显示标签
            "values": list[int],       # 各环节数量
            "step_rates": list[float], # 相对上一环节转化率
            "cumulative_rates": list[float], # 相对首层累计转化率
            "metrics": dict,           # CTR / CVR / DVR 等具名指标
        }
    """
    if df.empty:
        return {"steps": FUNNEL_STEPS, "labels": list(FUNNEL_LABELS.values()),
                "values": [0]*6, "step_rates": [0.0]*6, "cumulative_rates": [0.0]*6, "metrics": {}}

    values = [int(df[s].sum()) for s in FUNNEL_STEPS]
    step_rates = []
    cumulative_rates = []
    base = values[0] if values[0] > 0 else 1

    for i, v in enumerate(values):
        prev = values[i-1] if i > 0 else v
        step_rates.append(_safe_div(v, prev))
        cumulative_rates.append(_safe_div(v, base))

    imp, clk, dv, atc, ord_, pay = values
    metrics = {
        "CTR":              _safe_div(clk, imp),
        "Detail View Rate": _safe_div(dv,  clk),
        "Add to Cart Rate": _safe_div(atc, dv),
        "Order Rate":       _safe_div(ord_, atc),
        "Pay Rate":         _safe_div(pay, ord_),
        "CVR":              _safe_div(pay, clk),
    }

    return {
        "steps":            FUNNEL_STEPS,
        "labels":           list(FUNNEL_LABELS.values()),
        "values":           values,
        "step_rates":       step_rates,
        "cumulative_rates": cumulative_rates,
        "metrics":          metrics,
    }


def compare_funnel_by_group(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """按分组维度计算漏斗各环节指标。

    Args:
        df: 筛选后的数据集
        group_col: 分组字段，如 "channel" / "user_type" / "content_type"

    Returns:
        pd.DataFrame: 含 group_col / impression / click / ... / ctr / cvr / ... 列
    """
    if df.empty or group_col not in df.columns:
        return pd.DataFrame()

    grp = df.groupby(group_col).agg(
        impression  =("impression",  "sum"),
        click       =("click",       "sum"),
        detail_view =("detail_view", "sum"),
        add_to_cart =("add_to_cart", "sum"),
        order       =("order",       "sum"),
        pay         =("pay",         "sum"),
        pay_amount  =("pay_amount",  "sum"),
        campaign_cost=("campaign_cost","sum"),
    ).reset_index()

    grp["CTR"]              = grp.apply(lambda r: _safe_div(r.click,       r.impression),   axis=1)
    grp["Detail View Rate"] = grp.apply(lambda r: _safe_div(r.detail_view, r.click),        axis=1)
    grp["Add to Cart Rate"] = grp.apply(lambda r: _safe_div(r.add_to_cart, r.detail_view), axis=1)
    grp["Order Rate"]       = grp.apply(lambda r: _safe_div(r.order,       r.add_to_cart), axis=1)
    grp["Pay Rate"]         = grp.apply(lambda r: _safe_div(r.pay,         r.order),       axis=1)
    grp["CVR"]              = grp.apply(lambda r: _safe_div(r.pay,         r.click),       axis=1)
    grp["GMV"]              = grp["pay_amount"]
    grp["ROI"]              = grp.apply(lambda r: _safe_div(r.pay_amount,  r.campaign_cost), axis=1)

    return grp.sort_values("impression", ascending=False).reset_index(drop=True)


def detect_drop_stage(funnel_summary: dict, df: pd.DataFrame | None = None) -> dict:
    """自动判断问题位置和重点掉点环节。

    Args:
        funnel_summary: build_funnel_summary 的返回值
        df: 可选，用于计算全局基线

    Returns:
        dict: {
            "problem_type": str,   # "前链路问题" / "后链路问题" / "混合型问题" / "分群差异问题"
            "drop_stage": str,     # 最主要掉点环节
            "drop_rate": float,    # 该环节转化率
            "suggestion": list[str], # 策略建议方向
            "summary": str,        # 一句话摘要
            "details": list[str],  # 详细分析列表
        }
    """
    metrics = funnel_summary.get("metrics", {})
    step_rates = funnel_summary.get("step_rates", [])
    steps = funnel_summary.get("steps", FUNNEL_STEPS)

    if not metrics:
        return {"problem_type": "数据不足", "drop_stage": "", "drop_rate": 0,
                "suggestion": [], "summary": "暂无数据", "details": []}

    ctr = metrics.get("CTR", 0)
    cvr = metrics.get("CVR", 0)
    dvr = metrics.get("Detail View Rate", 0)
    acr = metrics.get("Add to Cart Rate", 0)
    orr = metrics.get("Order Rate", 0)
    prr = metrics.get("Pay Rate", 0)

    # 找出相对转化率最低的环节（跳过 impression → impression 自身）
    named_rates = {
        "CTR (曝光→点击)":              ctr,
        "Detail View Rate (点击→详情)": dvr,
        "Add to Cart Rate (详情→加购)": acr,
        "Order Rate (加购→下单)":       orr,
        "Pay Rate (下单→支付)":         prr,
    }
    drop_stage = min(named_rates, key=named_rates.get)
    drop_rate  = named_rates[drop_stage]

    # 问题类型判断
    front_chain_issue = ctr < 0.05   # CTR 低于绝对阈值
    back_chain_issue  = cvr < 0.10   # CVR 低于绝对阈值
    # 相对判断：CTR 是否显著低于 CVR 链路
    ctr_weak = ctr < 0.055
    cvr_weak = cvr < 0.12

    if ctr_weak and not cvr_weak:
        problem_type = "前链路问题"
        suggestion = [
            "优化内容展示形式（短视频 > 图文）",
            "调整分发人群匹配精度（高潜用户优先）",
            "优化标题、封面等吸引力元素",
            "进行 A/B Test：展示优化 vs 排序调整",
        ]
        details = [
            f"⚠️ CTR 为 {ctr*100:.2f}%，整体点击效率偏低",
            f"✅ CVR 为 {cvr*100:.2f}%，点击后转化尚可",
            f"💡 问题主要集中在曝光→点击环节，建议优先做展示优化和分发策略调整",
        ]
        summary = f"CTR 偏低 ({ctr*100:.2f}%)，前链路点击效率不足，重点优化展示与分发。"

    elif not ctr_weak and cvr_weak:
        problem_type = "后链路问题"
        suggestion = [
            "优化商品详情页承接信息（卖点、评价、促销信息）",
            "对高潜用户发放专属优惠券/补贴",
            "优化加购到支付的激励机制",
            "进行 A/B Test：详情承接优化 vs 优惠券发放",
        ]
        details = [
            f"✅ CTR 为 {ctr*100:.2f}%，点击效率尚可",
            f"⚠️ CVR 为 {cvr*100:.2f}%，整体转化明显偏弱",
            f"🔍 重点掉点：{drop_stage} = {drop_rate*100:.1f}%",
            f"💡 建议优先优化详情承接和交易激励策略",
        ]
        summary = f"CVR 偏低 ({cvr*100:.2f}%)，后链路承接转化不足，建议优先优化详情页和激励策略。"

    elif ctr_weak and cvr_weak:
        problem_type = "混合型问题"
        suggestion = [
            "优先修复流量规模更大的掉点环节",
            "同步排查前链路展示效率和后链路承接问题",
            "分场景、分人群拆解，确认问题集中位置",
            "建议先做小范围实验，验证后再逐步推进",
        ]
        details = [
            f"⚠️ CTR = {ctr*100:.2f}%，前链路偏弱",
            f"⚠️ CVR = {cvr*100:.2f}%，后链路也偏弱",
            f"🔍 重点掉点：{drop_stage}",
            "💡 前后链路均存在问题，建议分维度拆解后优先级排序",
        ]
        summary = f"CTR 和 CVR 同时偏低，前后链路均有优化空间，需分维度定位。"

    else:
        problem_type = "分群差异问题"
        suggestion = [
            "进一步拆解不同 channel / user_type / content_type 差异",
            "识别高收益人群，设计差异化策略",
            "验证整体均值下是否存在结构性不均衡",
            "考虑分群实验，验证差异化策略效果",
        ]
        details = [
            f"✅ CTR = {ctr*100:.2f}%，整体尚可",
            f"✅ CVR = {cvr*100:.2f}%，整体尚可",
            "💡 整体指标良好，但内部可能存在结构性差异，建议向下拆解",
        ]
        summary = f"整体指标尚可，建议深入拆解分群差异，寻找优化机会点。"

    return {
        "problem_type": problem_type,
        "drop_stage":   drop_stage,
        "drop_rate":    drop_rate,
        "suggestion":   suggestion,
        "summary":      summary,
        "details":      details,
        "named_rates":  named_rates,
    }


def get_attribution_summary(
    funnel_summary: dict,
    group_results: dict[str, pd.DataFrame],
    filters: dict,
) -> dict:
    """生成归因摘要，综合多维度对比结果。

    Args:
        funnel_summary: 全局漏斗摘要
        group_results: {"channel": df, "user_type": df, "content_type": df}
        filters: 当前筛选条件

    Returns:
        dict: 归因摘要，含受影响的场景/人群/内容类型
    """
    diagnosis = detect_drop_stage(funnel_summary)

    worst = {}
    for dim, df in group_results.items():
        if df.empty or "CTR" not in df.columns:
            continue
        idx = df["CTR"].idxmin()
        worst[dim] = df.loc[idx, dim] if dim in df.columns else "未知"

    return {
        "diagnosis":    diagnosis,
        "worst_groups": worst,
        "filters":      filters,
    }
