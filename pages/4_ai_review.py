"""
4_ai_review.py — AI 复盘与策略建议页

解决问题：将结构化分析结果和实验结果输入 AI，
          生成可读性强的复盘结论、分群收益分析、放量建议和后续优化方向。
"""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.data_loader import load_data, get_filter_options
from modules.filter_utils import build_filters_from_sidebar, apply_common_filters
from modules.metric_calculator import calc_core_metrics, calc_group_metrics, calc_period_comparison
from modules.funnel_analyzer import build_funnel_summary, compare_funnel_by_group, detect_drop_stage
from modules.ai_summary import generate_anomaly_summary, generate_review_summary
from modules.chart_builder import build_grouped_bar_chart, build_metric_bar_chart

st.set_page_config(page_title="AI 复盘与策略建议", page_icon="🤖", layout="wide")

st.markdown("""
<style>
.ai-output { background:white; border-radius:10px; padding:1.4rem;
             box-shadow:0 2px 10px rgba(0,0,0,0.08); border-left:5px solid #1E5799; margin:0.5rem 0; }
.ai-output.review { border-left-color:#27AE60; }
.input-card { background:#F5F7FA; border-radius:8px; padding:0.8rem 1rem; margin-bottom:0.5rem;
              border:1px solid #E8EDF0; }
.action-card { border-radius:8px; padding:0.8rem 1rem; margin-bottom:6px; font-size:0.87rem; }
.action-card.go { background:#EAFAF1; border-left:3px solid #27AE60; }
.action-card.stop { background:#FDEDEC; border-left:3px solid #E74C3C; }
.action-card.wait { background:#FEF9E7; border-left:3px solid #F39C12; }
.badge { display:inline-block; border-radius:12px; padding:3px 12px; font-size:0.78rem;
         font-weight:600; margin-left:6px; }
.badge.ai { background:#1E5799; color:white; }
.badge.fallback { background:#95A5A6; color:white; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
## 🤖 AI 复盘与策略建议页
<p style="color:#666;font-size:0.93rem;">
本页面基于结构化指标摘要、漏斗分析结果和实验组数据，生成异常诊断报告与实验复盘结论，
输出放量建议和后续优化方向。AI 仅做结构化总结，不替代人工最终判断。
</p>
<hr style="border-color:#E8EDF0;margin-bottom:1.2rem">
""", unsafe_allow_html=True)

# ── 数据加载 ──────────────────────────────────────────────────────────────────
df_full = load_data()

# ── 侧边栏筛选 ────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🎛️ 筛选条件")
filters = build_filters_from_sidebar(df_full, show_experiment=True, date_default_days=30)
df = apply_common_filters(df_full, filters)

if df.empty:
    st.warning("⚠️ 当前筛选条件下无数据，请调整筛选项。")
    st.stop()

st.sidebar.markdown(f"**当前数据量：{len(df):,} 行**")
st.sidebar.markdown("---")

# API Key 配置
with st.sidebar.expander("🔑 Claude API 配置（可选）"):
    api_key_input = st.text_input(
        "ANTHROPIC_API_KEY",
        type="password",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        help="填入后将调用真实 Claude API 生成内容，留空则使用预设输出"
    )
    if api_key_input:
        os.environ["ANTHROPIC_API_KEY"] = api_key_input
        st.success("✅ API Key 已设置")
    else:
        st.info("未配置 API Key，将使用预设示例输出")

# ── 预计算数据 ─────────────────────────────────────────────────────────────────
metrics         = calc_core_metrics(df)
comparison      = calc_period_comparison(df_full, filters, days=14)
metrics["comparison"] = comparison
funnel_summary  = build_funnel_summary(df)
diagnosis       = detect_drop_stage(funnel_summary)
funnel_summary["diagnosis"] = diagnosis

group_results = {
    "channel":      compare_funnel_by_group(df, "channel"),
    "user_type":    compare_funnel_by_group(df, "user_type"),
    "content_type": compare_funnel_by_group(df, "content_type"),
}

# 实验组对比
exp_results = {}
for eg in df["experiment_group"].unique():
    sub = df[df["experiment_group"] == eg]
    exp_results[eg] = calc_core_metrics(sub)

# ── Module 1: AI 异常诊断 ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🔍 模块一：AI 异常诊断")

col_input1, col_output1 = st.columns([1, 2])

with col_input1:
    st.markdown("**📥 输入依据摘要**")

    # 当前筛选上下文
    filter_parts = []
    if "date_range" in filters:
        dr = filters["date_range"]
        filter_parts.append(f"📅 {dr[0]} ~ {dr[1]}")
    for k, v in filters.items():
        if k == "date_range":
            continue
        if isinstance(v, list) and v:
            filter_parts.append(f"**{k}**: {', '.join(v)}")
    if filter_parts:
        st.markdown('<div class="input-card">' + "<br>".join(filter_parts) + "</div>", unsafe_allow_html=True)

    # 核心指标
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    ctr_v = metrics.get("ctr", 0)
    cvr_v = metrics.get("cvr", 0)
    gmv_v = metrics.get("gmv", 0)
    roi_v = metrics.get("roi", 0)
    nur_v = metrics.get("new_user_rate", 0)

    st.markdown(f"""
    **核心指标**
    - CTR: **{ctr_v*100:.2f}%**
    - CVR: **{cvr_v*100:.2f}%**
    - GMV: **¥{gmv_v/10000:.1f}万**
    - ROI: **{roi_v:.2f}x**
    - 新客率: **{nur_v*100:.1f}%**
    """)
    st.markdown("</div>", unsafe_allow_html=True)

    # 漏斗摘要
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.markdown(f"""
    **漏斗摘要**
    - 问题类型：{diagnosis.get('problem_type', '未知')}
    - 重点掉点：{diagnosis.get('drop_stage', '未知')}
    - 掉点转化率：{diagnosis.get('drop_rate', 0)*100:.1f}%
    """)
    st.markdown("</div>", unsafe_allow_html=True)

    # 触发按钮
    gen_anomaly = st.button("🤖 生成异常诊断报告", type="primary", use_container_width=True, key="gen_anomaly")

with col_output1:
    if gen_anomaly or "anomaly_output" in st.session_state:
        if gen_anomaly:
            with st.spinner("🤖 AI 正在分析，请稍候..."):
                input_data = {
                    "filters":       filters,
                    "metrics":       metrics,
                    "funnel_summary":funnel_summary,
                    "group_results": group_results,
                }
                text, is_real = generate_anomaly_summary(input_data)
                st.session_state["anomaly_output"] = text
                st.session_state["anomaly_is_real"] = is_real

        text    = st.session_state.get("anomaly_output", "")
        is_real = st.session_state.get("anomaly_is_real", False)

        badge = '<span class="badge ai">✨ Claude AI</span>' if is_real else '<span class="badge fallback">📝 示例输出</span>'
        st.markdown(f"""
        <div class="ai-output">
            <div style="font-size:0.78rem;color:#888;margin-bottom:0.8rem;">AI 异常诊断报告 {badge}</div>
        """, unsafe_allow_html=True)
        st.markdown(text)
        st.markdown("</div>", unsafe_allow_html=True)

        # 复制按钮
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.download_button(
                "⬇️ 下载诊断报告",
                data=text.encode("utf-8"),
                file_name="AI异常诊断报告.md",
                mime="text/markdown",
                use_container_width=True,
            )
    else:
        st.markdown("""
        <div style="background:#F5F7FA;border-radius:10px;padding:2.5rem;text-align:center;
                    color:#888;min-height:300px;display:flex;align-items:center;
                    justify-content:center;flex-direction:column;">
            <div style="font-size:2rem;margin-bottom:0.8rem;">🤖</div>
            <div style="font-weight:600;margin-bottom:0.4rem;">点击「生成异常诊断报告」</div>
            <div style="font-size:0.85rem;">系统将基于当前指标和漏斗数据生成结构化诊断</div>
        </div>
        """, unsafe_allow_html=True)

# ── Module 2: AI 实验复盘 ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 📊 模块二：AI 实验复盘")

# 实验组结果可视化
if exp_results and len(exp_results) > 1:
    st.markdown("### 实验组核心指标对比")
    exp_df = pd.DataFrame([
        {"experiment_group": eg, "ctr": m["ctr"], "cvr": m["cvr"],
         "gmv": m["gmv"]/10000, "roi": m["roi"]}
        for eg, m in exp_results.items()
    ])

    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        fig = build_metric_bar_chart(exp_df, x="experiment_group", y="ctr",
                                     title="实验组 CTR 对比", y_format="percent",
                                     global_avg=exp_df["ctr"].mean(), height=280)
        st.plotly_chart(fig, use_container_width=True)
    with col_e2:
        fig = build_metric_bar_chart(exp_df, x="experiment_group", y="cvr",
                                     title="实验组 CVR 对比", y_format="percent",
                                     global_avg=exp_df["cvr"].mean(), height=280)
        st.plotly_chart(fig, use_container_width=True)
    with col_e3:
        fig = build_metric_bar_chart(exp_df, x="experiment_group", y="roi",
                                     title="实验组 ROI 对比", y_format="number",
                                     global_avg=exp_df["roi"].mean(), height=280)
        st.plotly_chart(fig, use_container_width=True)

    # 实验结果详细数据
    with st.expander("展开实验组详细数据对比"):
        display_exp = exp_df.copy()
        display_exp["ctr"] = display_exp["ctr"].map(lambda x: f"{x*100:.2f}%")
        display_exp["cvr"] = display_exp["cvr"].map(lambda x: f"{x*100:.2f}%")
        display_exp["gmv"] = display_exp["gmv"].map(lambda x: f"¥{x:.1f}万")
        display_exp["roi"] = display_exp["roi"].map(lambda x: f"{x:.2f}x")
        display_exp.columns = ["实验组", "CTR", "CVR", "GMV（万元）", "ROI"]
        st.dataframe(display_exp, use_container_width=True, hide_index=True)

# 复盘信息输入
st.markdown("### 📝 实验基础信息（补充）")
col_review_form, col_review_output = st.columns([1, 2])

with col_review_form:
    with st.form("review_form"):
        exp_name = st.text_input("实验名称", value="recommendation_feed 展示优化实验")
        exp_goal = st.selectbox("实验目标", ["提升CTR", "提升CVR", "提升GMV", "提升新客支付率", "提升ROI"])
        exp_strategy = st.selectbox("策略类型", [
            "display_optimization", "ranking_adjustment",
            "detail_optimization", "coupon", "subsidy", "reactivation_push"
        ])
        target_ch = st.selectbox("目标场景", get_filter_options(df_full)["channel"] + ["all"])
        target_ug = st.selectbox("目标人群", get_filter_options(df_full)["user_type"] + ["all"])

        # 护栏指标评估
        st.markdown("**护栏指标评估**")
        control_m = exp_results.get("control", {})
        treat_m   = exp_results.get("treatment_a", exp_results.get("treatment", {}))
        roi_change  = (treat_m.get("roi", 0)  - control_m.get("roi", 0))  / max(control_m.get("roi", 1),  0.001)
        cost_change = (treat_m.get("campaign_cost_ratio", 0) - control_m.get("campaign_cost_ratio", 0)) if "campaign_cost_ratio" in treat_m else 0

        st.metric("treatment_a vs control | CTR uplift",
                  f"{(treat_m.get('ctr',0) - control_m.get('ctr',0))*100:+.2f}%")
        st.metric("treatment_a vs control | ROI 变化",
                  f"{roi_change*100:+.1f}%")

        gen_review = st.form_submit_button("🤖 生成实验复盘报告", type="primary", use_container_width=True)

with col_review_output:
    if gen_review or "review_output" in st.session_state:
        if gen_review:
            guardrail = {
                "ROI 变化":        f"{roi_change*100:+.1f}%（{'⚠️ 需关注' if roi_change < -0.05 else '✅ 正常'}）",
                "CTR uplift":       f"{(treat_m.get('ctr',0) - control_m.get('ctr',0))*100:+.2f}%",
                "CVR uplift":       f"{(treat_m.get('cvr',0) - control_m.get('cvr',0))*100:+.2f}%",
                "护栏评估结果":     "正常" if roi_change > -0.1 else "存在一定压力",
            }

            # 分群 uplift 摘要
            group_uplift = {}
            for dim, gdf in group_results.items():
                if gdf is not None and not gdf.empty and "CTR" in gdf.columns:
                    col_name = dim
                    top3 = gdf.nlargest(3, "CTR")
                    uplift_desc = {
                        str(row[col_name]): f"CTR={row['CTR']*100:.2f}%, CVR={row['CVR']*100:.2f}%"
                        for _, row in top3.iterrows()
                    }
                    group_uplift[f"Top {dim}"] = uplift_desc

            review_input = {
                "experiment_info": {
                    "实验名称":   exp_name,
                    "实验目标":   exp_goal,
                    "策略类型":   exp_strategy,
                    "目标场景":   target_ch,
                    "目标人群":   target_ug,
                    "实验周期":   "14天",
                },
                "result_summary":  exp_results,
                "group_uplift":    group_uplift,
                "guardrail_status":guardrail,
            }

            with st.spinner("🤖 AI 正在生成复盘报告..."):
                text, is_real = generate_review_summary(review_input)
                st.session_state["review_output"] = text
                st.session_state["review_is_real"] = is_real

        text    = st.session_state.get("review_output", "")
        is_real = st.session_state.get("review_is_real", False)

        badge = '<span class="badge ai">✨ Claude AI</span>' if is_real else '<span class="badge fallback">📝 示例输出</span>'
        st.markdown(f"""
        <div class="ai-output review">
            <div style="font-size:0.78rem;color:#888;margin-bottom:0.8rem;">AI 实验复盘报告 {badge}</div>
        """, unsafe_allow_html=True)
        st.markdown(text)
        st.markdown("</div>", unsafe_allow_html=True)

        st.download_button(
            "⬇️ 下载复盘报告",
            data=text.encode("utf-8"),
            file_name=f"{exp_name}_复盘报告.md",
            mime="text/markdown",
        )
    else:
        st.markdown("""
        <div style="background:#F5F7FA;border-radius:10px;padding:2.5rem;text-align:center;
                    color:#888;min-height:250px;display:flex;align-items:center;
                    justify-content:center;flex-direction:column;">
            <div style="font-size:2rem;margin-bottom:0.8rem;">📊</div>
            <div style="font-weight:600;">点击「生成实验复盘报告」</div>
        </div>
        """, unsafe_allow_html=True)

# ── Module 3: 放量建议 ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🚀 模块三：放量建议与后续动作")

# 自动计算放量建议
if exp_results and len(exp_results) > 1:
    control_m = exp_results.get("control", {})
    best_treat = None
    best_ctr_uplift = 0
    for eg, m in exp_results.items():
        if eg == "control":
            continue
        uplift = m.get("ctr", 0) - control_m.get("ctr", 0)
        if uplift > best_ctr_uplift:
            best_ctr_uplift = uplift
            best_treat = eg

    best_m = exp_results.get(best_treat, {}) if best_treat else {}
    ctr_up = (best_m.get("ctr", 0) - control_m.get("ctr", 0)) / max(control_m.get("ctr", 0.001), 0.001)
    cvr_up = (best_m.get("cvr", 0) - control_m.get("cvr", 0)) / max(control_m.get("cvr", 0.001), 0.001)
    roi_ok = best_m.get("roi", 0) >= control_m.get("roi", 0) * 0.9

    # 放量档位判断
    if ctr_up > 0.05 and cvr_up > 0 and roi_ok:
        rec_type = "go"
        rec_title = "✅ 建议继续放量"
        rec_desc  = f"treatment 组（{best_treat}）CTR 提升 {ctr_up*100:+.1f}%，CVR 同步改善，ROI 护栏稳定。建议对目标人群扩大覆盖范围继续验证。"
    elif ctr_up > 0.02 and not roi_ok:
        rec_type = "wait"
        rec_title = "⚠️ 建议局部分群放量"
        rec_desc  = f"CTR 有所提升（{ctr_up*100:+.1f}%），但 ROI 承压，建议仅对 high_potential_user 等高质量人群局部放量，严格监控成本。"
    else:
        rec_type = "stop"
        rec_title = "🔴 建议暂不放量，继续优化"
        rec_desc  = "当前实验结果未达预期，主指标提升有限或护栏指标异常。建议先调整策略范围或优化实验设计后再评估。"

    st.markdown(f"""
    <div class="action-card {rec_type}" style="padding:1rem 1.2rem;font-size:1rem;">
        <strong>{rec_title}</strong><br>
        <span style="font-size:0.87rem;color:#555;margin-top:4px;display:block;">{rec_desc}</span>
    </div>
    """, unsafe_allow_html=True)

# 后续动作建议
st.markdown("**📋 后续动作建议**")
col_a1, col_a2, col_a3, col_a4 = st.columns(4)

actions = {
    "📈 分析动作": [
        "继续拆解高价格带商品支付问题",
        "补充分场景 ROI 分析",
        "对比 treatment_a/b 的 CVR 分群差异",
    ],
    "🛠️ 策略动作": [
        "优先对 high_potential_user 保留最优实验组策略",
        "在 recommendation_feed 继续优化 short_video 展示",
        "暂缓高成本方案，优先验证轻量策略",
    ],
    "🧪 实验动作": [
        "开启二轮分群实验，聚焦 new_user",
        "将不同 channel 单独设组验证",
        "缩小补贴范围后重测 ROI",
    ],
    "🛡️ 风控动作": [
        "设置 ROI 护栏下限（建议 ≥ 0.8x）",
        "控制 campaign_cost 增幅上限",
        "暂不扩大低 ROI 人群覆盖",
    ],
}

for col, (action_type, items) in zip([col_a1, col_a2, col_a3, col_a4], actions.items()):
    with col:
        st.markdown(f"**{action_type}**")
        for item in items:
            st.markdown(f"""
            <div style="background:#F5F7FA;border-radius:6px;padding:5px 8px;
                        margin-bottom:4px;font-size:0.82rem;border:1px solid #E8EDF0;">
                {item}
            </div>
            """, unsafe_allow_html=True)

# ── 导出区 ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📤 结果导出")

anomaly_text = st.session_state.get("anomaly_output", "（尚未生成异常诊断报告）")
review_text  = st.session_state.get("review_output",  "（尚未生成实验复盘报告）")

full_report = f"""# AI 复盘与策略建议报告

## 异常诊断摘要

{anomaly_text}

---

## 实验复盘结论

{review_text}

---

## 后续动作建议

### 分析动作
{chr(10).join(['- ' + a for a in actions['📈 分析动作']])}

### 策略动作
{chr(10).join(['- ' + a for a in actions['🛠️ 策略动作']])}

### 实验动作
{chr(10).join(['- ' + a for a in actions['🧪 实验动作']])}

### 风控动作
{chr(10).join(['- ' + a for a in actions['🛡️ 风控动作']])}

---
*由 AI 复盘与策略建议页自动生成 · 抖音电商平台分发增长与策略优化工作台*
"""

col_dl1, col_dl2 = st.columns(2)
with col_dl1:
    st.download_button(
        "⬇️ 下载完整复盘报告（Markdown）",
        data=full_report.encode("utf-8"),
        file_name="完整复盘报告.md",
        mime="text/markdown",
        use_container_width=True,
    )
with col_dl2:
    st.info("💡 复盘报告可直接粘贴到 Notion、周报或 GitHub 文档中使用。")

# 侧边栏说明
st.sidebar.markdown("""
---
## 📖 模块说明

### 模块一：AI 异常诊断
- 基于当前指标摘要和漏斗分析自动生成
- 输出问题定位、原因方向和优先动作

### 模块二：AI 实验复盘
- 基于实验组对比数据生成
- 输出复盘结论和放量建议

### 模块三：放量建议
- 自动评估是否建议放量
- 输出具体后续动作

---
⚠️ **AI 风险控制**
- 核心数值由 pandas 计算，AI 不做数值运算
- 所有结论基于当前筛选数据范围
- 最终决策仍需结合业务背景
""")
