"""
ai_summary.py — AI 输入组装与输出渲染模块

职责：组装结构化 Prompt，调用 Claude API，返回结构化文本。
      API 不可用时展示预设占位输出，保证页面完整性。
"""
from __future__ import annotations
import os
import time
from dotenv import load_dotenv

load_dotenv()

# ── Prompt 模板（集中维护） ────────────────────────────────────────────────────
ANOMALY_PROMPT_TEMPLATE = """你是一位抖音电商平台的资深策略产品经理，具备深厚的推荐系统、增长运营和数据分析经验。

现在请你基于以下结构化分析数据，输出一份专业的异常诊断报告：

## 当前分析上下文
{context}

## 核心指标摘要
{metrics_summary}

## 漏斗分析结果
{funnel_summary}

## 分群差异摘要
{group_summary}

请严格按照以下结构输出（使用 Markdown 格式），不要编造数据外的结论：

### 🔍 问题摘要
（一句话描述当前主要异常现象）

### 📍 问题位置判断
（明确判断：前链路问题 / 后链路问题 / 混合型问题 / 分群差异问题）

### 💡 可能原因
（2-4条，需与场景/人群/内容类型数据相关）
- 原因1
- 原因2
- 原因3

### 🎯 影响范围
（说明最受影响的场景、人群、内容类型）

### ⚡ 建议优先动作
（按优先级排列，2-3条）
- 动作1
- 动作2

### ⚠️ 风险提醒
（1-2条关键注意事项）

注意：所有结论必须基于上方提供的数据，不得引用数据外信息。
"""

REVIEW_PROMPT_TEMPLATE = """你是一位抖音电商平台的资深策略产品经理，现在请基于以下实验结果数据，生成一份专业的实验复盘报告：

## 实验基础信息
{experiment_info}

## 实验结果摘要
{result_summary}

## 分群收益摘要
{group_uplift}

## 护栏指标状态
{guardrail_status}

请严格按照以下结构输出（使用 Markdown 格式）：

### 📊 实验结果摘要
（概述实验整体表现，主指标是否达到预期）

### 🔑 关键结论
（2-3条核心发现）
- 结论1
- 结论2

### 👥 分群收益结论
（哪些人群/场景收益更高，哪些提升有限）

### 🛡️ 风险与护栏结论
（护栏指标是否正常，是否有异常压力）

### 🚀 放量建议
（从以下三档选一：建议继续放量 / 建议局部分群放量 / 建议暂不放量 + 理由）

### 📋 后续优化方向
（2-3条具体建议）
- 建议1
- 建议2

注意：所有结论必须基于上方提供的数据，不得引用数据外信息。
"""

# ── 预设占位输出（API 不可用时使用） ─────────────────────────────────────────
ANOMALY_FALLBACK = """### 🔍 问题摘要
当前筛选条件下，recommendation_feed 场景的 CTR 低于整体均值约 12%，前链路点击效率明显不足。

### 📍 问题位置判断
**前链路问题** — CTR 偏低，曝光到点击环节存在明显效率损失。

### 💡 可能原因
- **内容形式与场景不匹配**：image_text 内容在 recommendation_feed 中 CTR 显著低于 short_video
- **人群匹配精度不足**：new_user 在当前场景下 CTR 低于 high_potential_user 约 15%
- **展示样式吸引力不足**：封面图、标题等展示元素未针对目标人群优化

### 🎯 影响范围
主要集中在 recommendation_feed 场景 + new_user 人群 + image_text 内容类型的交叉组合。

### ⚡ 建议优先动作
- **优先**：对 recommendation_feed 中的 image_text 内容进行展示优化实验，验证 short_video 替代效果
- **其次**：针对 new_user 设计更精准的人群匹配策略，提升分发精度

### ⚠️ 风险提醒
- 展示优化需同步观察 CVR 护栏指标，避免 CTR 提升但后链路质量下降
- 当前结论基于现有数据筛选范围，不应直接外推至全量场景
"""

REVIEW_FALLBACK = """### 📊 实验结果摘要
本次实验在目标场景中运行 14 天。treatment_a 组（排序调整策略）在 CTR 上相比 control 提升约 11.2%，CVR 基本持平，GMV 整体提升约 8.5%。

### 🔑 关键结论
- treatment_a 的 CTR 提升效果显著，说明排序调整对前链路点击效率有正向作用
- CVR 和 GMV 同步改善，验证了"提升点击 → 带动成交"的假设基本成立
- treatment_b（优惠券组）GMV 提升更高但 ROI 有所承压，需谨慎推广

### 👥 分群收益结论
high_potential_user 和 returning_user 在 treatment_a 中提升更为明显，new_user 提升有限，建议优先对高潜和回流用户放量。

### 🛡️ 风险与护栏结论
treatment_a 的 ROI 和 campaign_cost 基本稳定，护栏指标正常。treatment_b 的 campaign_cost 提升约 32%，ROI 有所下降，建议控制覆盖范围。

### 🚀 放量建议
**建议局部分群放量** — 对 high_potential_user 和 returning_user 继续放量 treatment_a，暂不推广至全量。treatment_b 建议优化成本结构后再评估。

### 📋 后续优化方向
- 针对 new_user 设计专属低门槛激励实验，弥补当前策略对新客效果不足的问题
- 对 treatment_b 优惠券方案做成本优化，控制 campaign_cost，提升 ROI 至合理水平
- 进一步拆解 electronics 等高客单价类目的策略效果，评估差异化处理可行性
"""


def _build_context_str(input_data: dict) -> str:
    """将输入数据转为上下文字符串。"""
    filters = input_data.get("filters", {})
    parts = []
    if "date_range" in filters:
        dr = filters["date_range"]
        parts.append(f"- 分析周期：{dr[0]} 至 {dr[1]}")
    for k, v in filters.items():
        if k == "date_range":
            continue
        if isinstance(v, list) and v:
            parts.append(f"- {k}：{', '.join(str(i) for i in v)}")
    return "\n".join(parts) if parts else "全量数据（未做额外筛选）"


def _build_metrics_str(metrics: dict) -> str:
    """格式化核心指标摘要。"""
    lines = [
        f"- CTR: {metrics.get('ctr', 0)*100:.2f}%",
        f"- CVR: {metrics.get('cvr', 0)*100:.2f}%",
        f"- GMV: ¥{metrics.get('gmv', 0)/10000:.1f} 万",
        f"- ROI: {metrics.get('roi', 0):.2f}x",
        f"- New User Rate: {metrics.get('new_user_rate', 0)*100:.1f}%",
        f"- 总曝光: {metrics.get('impression', 0):,}",
        f"- 总点击: {metrics.get('click', 0):,}",
        f"- 总支付: {metrics.get('pay', 0):,}",
    ]
    # 环比
    comparison = metrics.get("comparison", {})
    for key, label in [("ctr", "CTR"), ("cvr", "CVR"), ("gmv", "GMV")]:
        if key in comparison:
            chg = comparison[key].get("change_pct", 0)
            sign = "↑" if chg > 0 else "↓"
            lines.append(f"- {label} 环比：{sign} {abs(chg)*100:.1f}%")
    return "\n".join(lines)


def _build_funnel_str(funnel_summary: dict) -> str:
    """格式化漏斗摘要。"""
    if not funnel_summary or not funnel_summary.get("metrics"):
        return "漏斗数据不可用"
    m = funnel_summary["metrics"]
    vals = funnel_summary.get("values", [])
    steps = funnel_summary.get("labels", [])
    lines = []
    for i, (s, v) in enumerate(zip(steps, vals)):
        rate = funnel_summary["step_rates"][i] if i < len(funnel_summary["step_rates"]) else 0
        rate_str = f"（转化率 {rate*100:.1f}%）" if i > 0 else ""
        lines.append(f"- {s}: {v:,} {rate_str}")
    diag = funnel_summary.get("diagnosis", {})
    if diag:
        lines.append(f"\n问题类型：{diag.get('problem_type', '未知')}")
        lines.append(f"重点掉点：{diag.get('drop_stage', '未知')}")
    return "\n".join(lines)


def _build_group_str(group_results: dict) -> str:
    """格式化分群摘要。"""
    lines = []
    for dim, df in group_results.items():
        if df is None or df.empty or "CTR" not in df.columns:
            continue
        lines.append(f"\n**按 {dim} 分组：**")
        col = dim if dim in df.columns else df.columns[0]
        for _, row in df.iterrows():
            name = row.get(col, "未知")
            ctr  = row.get("CTR", 0)
            cvr  = row.get("CVR", 0)
            gmv  = row.get("GMV", 0)
            lines.append(f"  - {name}: CTR={ctr*100:.2f}%, CVR={cvr*100:.2f}%, GMV=¥{gmv/10000:.1f}万")
    return "\n".join(lines) if lines else "分群数据不可用"


def _call_claude_api(prompt: str, max_tokens: int = 1200) -> str | None:
    """调用 Claude API，失败返回 None。"""
    # 优先读取 Streamlit Cloud Secrets，其次读取环境变量（本地 .env）
    try:
        import streamlit as st
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
    except Exception:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=max_tokens,
            timeout=30,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        print(f"[ai_summary] Claude API 调用失败: {e}")
        return None


def generate_anomaly_summary(input_data: dict) -> tuple[str, bool]:
    """生成异常诊断摘要。

    Args:
        input_data: {
            "filters": dict,
            "metrics": dict,
            "funnel_summary": dict,
            "group_results": dict,
        }

    Returns:
        tuple[str, bool]: (输出文本, 是否为真实AI输出)
    """
    prompt = ANOMALY_PROMPT_TEMPLATE.format(
        context        = _build_context_str(input_data),
        metrics_summary= _build_metrics_str(input_data.get("metrics", {})),
        funnel_summary = _build_funnel_str(input_data.get("funnel_summary", {})),
        group_summary  = _build_group_str(input_data.get("group_results", {})),
    )
    result = _call_claude_api(prompt)
    if result:
        return result, True
    return ANOMALY_FALLBACK, False


def generate_review_summary(input_data: dict) -> tuple[str, bool]:
    """生成实验复盘摘要。

    Args:
        input_data: {
            "experiment_info": dict,
            "result_summary": dict,   # {group: {metric: value}}
            "group_uplift": dict,
            "guardrail_status": dict,
        }

    Returns:
        tuple[str, bool]: (输出文本, 是否为真实AI输出)
    """
    # 组装实验信息
    exp_info = input_data.get("experiment_info", {})
    exp_str = "\n".join([f"- {k}: {v}" for k, v in exp_info.items()])

    # 结果摘要
    result = input_data.get("result_summary", {})
    result_lines = []
    for group, metrics in result.items():
        if isinstance(metrics, dict):
            ctr = metrics.get("ctr", 0)
            cvr = metrics.get("cvr", 0)
            gmv = metrics.get("gmv", 0)
            roi = metrics.get("roi", 0)
            result_lines.append(
                f"- {group}: CTR={ctr*100:.2f}%, CVR={cvr*100:.2f}%, GMV=¥{gmv/10000:.1f}万, ROI={roi:.2f}x"
            )
    result_str = "\n".join(result_lines) if result_lines else "结果数据不可用"

    # 分群 uplift
    uplift = input_data.get("group_uplift", {})
    uplift_lines = []
    for dim, data in uplift.items():
        uplift_lines.append(f"\n**{dim} 维度 uplift：**")
        if isinstance(data, dict):
            for k, v in data.items():
                uplift_lines.append(f"  - {k}: {v}")
    uplift_str = "\n".join(uplift_lines) if uplift_lines else "分群数据不可用"

    # 护栏
    guardrail = input_data.get("guardrail_status", {})
    guardrail_str = "\n".join([f"- {k}: {v}" for k, v in guardrail.items()]) if guardrail else "护栏数据不可用"

    prompt = REVIEW_PROMPT_TEMPLATE.format(
        experiment_info = exp_str,
        result_summary  = result_str,
        group_uplift    = uplift_str,
        guardrail_status= guardrail_str,
    )
    result_text = _call_claude_api(prompt)
    if result_text:
        return result_text, True
    return REVIEW_FALLBACK, False
