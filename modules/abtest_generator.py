"""
abtest_generator.py — 实验方案自动生成模块

职责：根据表单输入生成结构化实验方案和 Markdown 文本。
"""
from __future__ import annotations


# ── 指标推荐规则库 ─────────────────────────────────────────────────────────────
GOAL_METRICS = {
    "提升CTR":     {"primary": ["CTR"], "secondary": ["Impression", "Detail View Rate", "CTR by Channel", "CTR by Content Type"], "guardrail": ["CVR", "GMV", "ROI"]},
    "提升CVR":     {"primary": ["CVR"], "secondary": ["Detail View Rate", "Add to Cart Rate", "Order Rate", "Pay Rate", "GMV"], "guardrail": ["ROI", "Campaign Cost", "Pay Rate 波动"]},
    "提升GMV":     {"primary": ["GMV"], "secondary": ["CVR", "Pay Count", "Avg Pay Amount", "New User Rate", "ROI"], "guardrail": ["ROI", "Campaign Cost Ratio", "Pay Rate"]},
    "提升新客支付率":{"primary": ["New User Rate", "New User Pay Count"], "secondary": ["CTR", "CVR", "New User GMV"], "guardrail": ["Campaign Cost", "ROI", "Overall CVR"]},
    "提升召回点击率":{"primary": ["Reactivation CTR", "CTR"], "secondary": ["Returning User CVR", "GMV"], "guardrail": ["ROI", "Campaign Cost", "Returning User CVR"]},
    "提升ROI":     {"primary": ["ROI"], "secondary": ["GMV", "CVR", "Campaign Cost Ratio"], "guardrail": ["CTR 不得显著下降", "CVR", "GMV"]},
}

STRATEGY_RISK = {
    "display_optimization":  ["CTR 提升不一定带动 CVR 同步改善，需同步观察后链路", "内容形式调整可能影响部分人群偏好"],
    "ranking_adjustment":    ["流量重新分配可能影响整体曝光分布", "需观察护栏指标是否异常波动"],
    "detail_optimization":   ["详情页改版可能影响短期 A/B 实验结论稳定性", "需控制实验组覆盖范围避免影响全量"],
    "coupon":                ["优惠券成本较高，需重点关注 ROI 和 Campaign Cost", "优惠券可能带来羊毛用户，影响长期质量"],
    "subsidy":               ["补贴成本敏感，建议设置 ROI 护栏下限", "需区分真实增量需求与补贴刺激需求"],
    "reactivation_push":     ["触达成本较高，ROI 回收周期较长", "召回效果对用户沉默时长敏感"],
}

DURATION_RULES = {
    "提升CTR":     7,
    "提升CVR":     14,
    "提升GMV":     14,
    "提升新客支付率": 14,
    "提升召回点击率": 21,
    "提升ROI":     21,
}

GROUPING_RULES = {
    "display_optimization":  "双组",
    "ranking_adjustment":    "双组",
    "detail_optimization":   "双组",
    "coupon":                "三组",
    "subsidy":               "三组",
    "reactivation_push":     "双组",
}


def generate_abtest_plan(input_params: dict) -> dict:
    """根据表单输入生成完整的实验方案。

    Args:
        input_params: {
            "strategy_name": str,
            "business_goal": str,        # 提升CTR / 提升CVR / 提升GMV / ...
            "problem_type": str,         # low_ctr / low_conversion / low_roi / ...
            "strategy_type": str,        # display_optimization / coupon / ...
            "hypothesis": str,
            "target_channel": str,
            "target_user_group": str,
            "target_content_type": str,
            "target_item_category": str,
            "target_price_band": str,
            "experiment_duration_preference": str, # auto / 7_days / 14_days / 21_days
            "cost_sensitive_flag": bool,
            "risk_note": str,
        }

    Returns:
        dict: {
            "plan": dict,           # 结构化实验方案
            "markdown": str,        # 可复制的 Markdown 文本
        }
    """
    goal         = input_params.get("business_goal", "提升CVR")
    strategy     = input_params.get("strategy_type", "detail_optimization")
    name         = input_params.get("strategy_name", "新实验")
    hypothesis   = input_params.get("hypothesis", "（待补充实验假设）")
    channel      = input_params.get("target_channel", "recommendation_feed")
    user_group   = input_params.get("target_user_group", "all_users")
    content_type = input_params.get("target_content_type", "all")
    item_cat     = input_params.get("target_item_category", "all")
    price_band   = input_params.get("target_price_band", "all")
    duration_pref= input_params.get("experiment_duration_preference", "auto")
    cost_flag    = input_params.get("cost_sensitive_flag", False)
    risk_note    = input_params.get("risk_note", "")
    problem_type = input_params.get("problem_type", "low_conversion")

    # 指标推荐
    metrics_conf = GOAL_METRICS.get(goal, GOAL_METRICS["提升CVR"])
    primary      = metrics_conf["primary"]
    secondary    = metrics_conf["secondary"]
    guardrail    = metrics_conf["guardrail"]

    if cost_flag and "ROI" not in guardrail:
        guardrail = ["ROI", "Campaign Cost"] + guardrail
    if cost_flag and "Campaign Cost" not in guardrail:
        guardrail = ["Campaign Cost"] + guardrail

    # 观察周期
    if duration_pref == "auto":
        base_days = DURATION_RULES.get(goal, 14)
        if price_band == "high" or cost_flag:
            base_days = max(base_days, 21)
    else:
        day_map = {"7_days": 7, "14_days": 14, "21_days": 21}
        base_days = day_map.get(duration_pref, 14)

    duration_label = f"{base_days} 天"
    if base_days == 7:
        duration_reason = "当前实验主要验证前链路点击效率，7天周期足以观察趋势。"
    elif base_days == 21:
        duration_reason = "当前实验涉及高价格带商品或成本敏感场景，建议21天以确保结论稳定。"
    else:
        duration_reason = "14天为标准实验周期，能兼顾结果稳定性和推进效率。"

    # 分组建议
    grouping_type = GROUPING_RULES.get(strategy, "双组")
    if grouping_type == "双组":
        groups = {
            "control":   "维持当前策略，不做额外干预",
            "treatment": f"对目标范围应用【{_strategy_label(strategy)}】策略",
        }
        success_criteria = f"treatment 组 {primary[0]} 显著高于 control 组（建议提升 ≥5%），且护栏指标无异常下跌。"
    else:
        groups = {
            "control":     "维持当前策略，不做额外干预",
            "treatment_a": f"轻量版【{_strategy_label(strategy)}】（低强度策略）",
            "treatment_b": f"增强版【{_strategy_label(strategy)}】（高强度策略）",
        }
        success_criteria = f"treatment_a / treatment_b 的 {primary[0]} 显著高于 control，ROI 在可接受范围内。"

    # 风险
    risks = list(STRATEGY_RISK.get(strategy, ["请结合业务背景补充风险点"]))
    if risk_note:
        risks.append(f"⚠️ 额外风险备注：{risk_note}")
    if cost_flag:
        risks.insert(0, "💰 成本敏感：需重点监控 Campaign Cost 和 ROI，建议设置护栏下限。")

    # 问题背景
    problem_desc = _problem_desc(problem_type, channel, user_group)

    # 复盘重点
    review_focus = [
        f"重点对比 {primary[0]} 在不同 experiment_group 间的差异",
        f"拆解 {channel} 场景下 {user_group} 人群的 uplift 情况",
        f"验证护栏指标 {guardrail[0]} 是否保持稳定",
        "观察是否存在显著的分群差异，判断是否适合局部放量",
    ]

    plan = {
        "strategy_name":       name,
        "business_goal":       goal,
        "problem_background":  problem_desc,
        "hypothesis":          hypothesis,
        "target": {
            "channel":          channel,
            "user_group":       user_group,
            "content_type":     content_type,
            "item_category":    item_cat,
            "price_band":       price_band,
        },
        "groups":              groups,
        "primary_metrics":     primary,
        "secondary_metrics":   secondary,
        "guardrail_metrics":   guardrail,
        "duration":            duration_label,
        "duration_reason":     duration_reason,
        "success_criteria":    success_criteria,
        "risks":               risks,
        "review_focus":        review_focus,
        "strategy_type":       strategy,
    }

    markdown = _generate_markdown(plan)
    return {"plan": plan, "markdown": markdown}


def _strategy_label(strategy: str) -> str:
    labels = {
        "display_optimization":  "展示优化",
        "ranking_adjustment":    "排序调整",
        "detail_optimization":   "详情承接优化",
        "coupon":                "优惠券发放",
        "subsidy":               "补贴激励",
        "reactivation_push":     "召回触达",
    }
    return labels.get(strategy, strategy)


def _problem_desc(problem_type: str, channel: str, user_group: str) -> str:
    descs = {
        "low_ctr":         f"当前 {channel} 场景下，{user_group} 人群的 CTR 低于预期，前链路点击效率不足。",
        "low_conversion":  f"当前 {channel} 场景下，点击后的 CVR 偏低，后链路承接与交易转化存在问题。",
        "low_roi":         f"当前 {channel} 场景下，ROI 低于预期，策略成本回收效率偏低。",
        "group_difference":f"当前整体指标尚可，但不同人群或场景间存在明显差异，{user_group} 表现待优化。",
        "reactivation_need":f"当前 {user_group} 沉默用户较多，需通过召回策略提升复购和回流。",
    }
    return descs.get(problem_type, f"当前 {channel} 场景存在策略优化机会，目标人群 {user_group}。")


def _generate_markdown(plan: dict) -> str:
    t = plan["target"]
    groups_md = "\n".join([f"- **{k}**: {v}" for k, v in plan["groups"].items()])
    risks_md  = "\n".join([f"- {r}" for r in plan["risks"]])
    review_md = "\n".join([f"- {r}" for r in plan["review_focus"]])
    primary_md   = " / ".join(plan["primary_metrics"])
    secondary_md = " / ".join(plan["secondary_metrics"])
    guardrail_md = " / ".join(plan["guardrail_metrics"])

    return f"""## 实验方案：{plan["strategy_name"]}

### 背景问题
{plan["problem_background"]}

### 实验目标
{plan["business_goal"]}

### 实验假设
{plan["hypothesis"]}

### 实验对象
- 场景：{t["channel"]}
- 人群：{t["user_group"]}
- 内容类型：{t["content_type"]}
- 商品类目：{t["item_category"]}
- 价格带：{t["price_band"]}

### 分组方式
{groups_md}

### 主指标
{primary_md}

### 辅助指标
{secondary_md}

### 护栏指标
{guardrail_md}

### 观察周期
{plan["duration"]} — {plan["duration_reason"]}

### 成功判定标准
{plan["success_criteria"]}

### 风险提示
{risks_md}

### 复盘重点
{review_md}

---
*由 A/B Test 设计助手自动生成 · 抖音电商平台分发增长与策略优化工作台*
"""
