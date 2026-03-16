"""
2_funnel_analysis.py — 漏斗分析与归因页

解决问题：将 Dashboard 发现的异常进一步拆解到具体漏斗环节，
          判断是前链路（展示→点击）还是后链路（点击→支付）问题，
          输出结构化问题定位与策略方向建议。
"""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.data_loader import load_data
from modules.filter_utils import build_filters_from_sidebar, apply_common_filters
from modules.metric_calculator import calc_group_metrics
from modules.funnel_analyzer import build_funnel_summary, compare_funnel_by_group, detect_drop_stage
from modules.chart_builder import (
    build_funnel_chart, build_metric_bar_chart, build_grouped_bar_chart,
    PRIMARY, DANGER, SUCCESS, WARNING
)

st.set_page_config(page_title="漏斗分析与归因", page_icon="🔍", layout="wide")

st.markdown("""
<style>
.metric-row { display:flex; gap:12px; margin:0.5rem 0; flex-wrap:wrap; }
.mini-card { background:white; border-radius:8px; padding:0.7rem 1rem; flex:1; min-width:120px;
             box-shadow:0 1px 6px rgba(0,0,0,0.07); border-top:3px solid #1E5799; text-align:center; }
.mini-card.bad { border-top-color:#E74C3C; }
.mini-card.good { border-top-color:#27AE60; }
.diagnosis-card { background:white; border-radius:10px; padding:1.2rem; box-shadow:0 2px 8px rgba(0,0,0,0.08);
                  border-left:5px solid #1E5799; margin-bottom:1rem; }
.diagnosis-card.front { border-left-color:#E74C3C; }
.diagnosis-card.back  { border-left-color:#F39C12; }
.diagnosis-card.mixed { border-left-color:#9B59B6; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
## 🔍 漏斗分析与归因页
<p style="color:#666;font-size:0.93rem;">
围绕曝光→点击→详情→加购→下单→支付全链路，识别重点掉点环节，结合场景/人群/内容类型差异进行问题定位，
为后续 A/B Test 设计提供结构化输入。
</p>
<hr style="border-color:#E8EDF0;margin-bottom:1.2rem">
""", unsafe_allow_html=True)

# ── 数据加载 & 筛选 ───────────────────────────────────────────────────────────
df_full = load_data()
st.sidebar.markdown("## 🎛️ 筛选条件")
filters = build_filters_from_sidebar(df_full, show_experiment=True, date_default_days=14)
df = apply_common_filters(df_full, filters)

if df.empty:
    st.warning("⚠️ 当前筛选条件下无数据，请调整筛选项。")
    st.stop()

st.sidebar.markdown(f"**当前数据量：{len(df):,} 行**")

# ── Section 1: 全局漏斗 ───────────────────────────────────────────────────────
st.markdown("### 📐 全局漏斗概览")
col_funnel, col_metrics = st.columns([3, 2])

funnel_summary = build_funnel_summary(df)

with col_funnel:
    fig = build_funnel_chart(
        stages=funnel_summary["labels"],
        values=funnel_summary["values"],
        title="全链路漏斗（当前筛选范围）",
        height=430,
    )
    st.plotly_chart(fig, use_container_width=True)

with col_metrics:
    st.markdown("**漏斗各环节转化率**")
    metrics_map = funnel_summary["metrics"]
    step_rates   = funnel_summary["step_rates"]
    steps        = funnel_summary["steps"]
    labels       = funnel_summary["labels"]
    values       = funnel_summary["values"]

    # 展示每层卡片
    for i, (step, label, val, sr) in enumerate(zip(steps, labels, values, step_rates)):
        if i == 0:
            st.markdown(f"""
            <div class="mini-card">
                <div style="font-size:0.75rem;color:#888;">{label}</div>
                <div style="font-size:1.3rem;font-weight:700;">{val:,.0f}</div>
                <div style="font-size:0.75rem;color:#1E5799;">起始层（100%）</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            card_cls = "bad" if sr < 0.5 else ("good" if sr > 0.85 else "")
            st.markdown(f"""
            <div class="mini-card {card_cls}">
                <div style="font-size:0.75rem;color:#888;">{label}</div>
                <div style="font-size:1.3rem;font-weight:700;">{val:,.0f}</div>
                <div style="font-size:0.75rem;color:{'#E74C3C' if card_cls=='bad' else '#27AE60' if card_cls=='good' else '#666'};">
                    转化率 {sr*100:.1f}%
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**核心链路指标**")
    for name, val in metrics_map.items():
        bar_pct = min(val * 100, 100)
        color = "#E74C3C" if val < 0.3 else ("#F39C12" if val < 0.6 else "#27AE60")
        st.markdown(f"""
        <div style="margin-bottom:6px;">
            <div style="display:flex;justify-content:space-between;font-size:0.82rem;">
                <span style="color:#555;">{name}</span>
                <span style="font-weight:600;color:{color};">{val*100:.2f}%</span>
            </div>
            <div style="background:#E8EDF0;border-radius:4px;height:6px;">
                <div style="background:{color};width:{bar_pct}%;height:6px;border-radius:4px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Section 2: 对比分析 ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📊 多维度漏斗对比分析")
st.caption("按不同维度拆解漏斗差异，识别是整体性问题还是结构性问题")

tab1, tab2, tab3 = st.tabs(["📡 按流量场景", "👤 按用户类型", "🎬 按内容类型"])

FUNNEL_METRICS = ["CTR", "Detail View Rate", "Add to Cart Rate", "Order Rate", "Pay Rate", "CVR"]

def render_comparison_tab(tab, group_col: str, label: str):
    with tab:
        group_df = compare_funnel_by_group(df, group_col)
        if group_df.empty:
            st.info("数据不足，无法展示对比。")
            return

        # 指标选择
        sel_metrics = st.multiselect(
            f"选择对比指标（{label}维度）",
            FUNNEL_METRICS,
            default=["CTR", "CVR"],
            key=f"sel_{group_col}"
        )
        if not sel_metrics:
            st.warning("请至少选择一个指标")
            return

        col_charts = st.columns(min(len(sel_metrics), 2))
        for i, metric in enumerate(sel_metrics):
            if metric not in group_df.columns:
                continue
            global_avg = group_df[metric].mean()
            with col_charts[i % 2]:
                fig = build_metric_bar_chart(
                    group_df, x=group_col, y=metric,
                    title=f"{label} × {metric}",
                    height=300,
                    y_format="percent",
                    global_avg=global_avg,
                )
                st.plotly_chart(fig, use_container_width=True)

        # 对比数据表
        with st.expander(f"展开 {label} 详细对比数据"):
            display_cols = [group_col] + [m for m in FUNNEL_METRICS if m in group_df.columns] + ["GMV", "ROI"]
            display_cols = [c for c in display_cols if c in group_df.columns]
            d = group_df[display_cols].copy()
            for c in FUNNEL_METRICS:
                if c in d.columns:
                    d[c] = d[c].map(lambda x: f"{x*100:.2f}%")
            if "GMV" in d.columns:
                d["GMV"] = d["GMV"].map(lambda x: f"¥{x/10000:.1f}万")
            if "ROI" in d.columns:
                d["ROI"] = d["ROI"].map(lambda x: f"{x:.2f}x")
            st.dataframe(d, use_container_width=True, hide_index=True)

render_comparison_tab(tab1, "channel",      "流量场景")
render_comparison_tab(tab2, "user_type",    "用户类型")
render_comparison_tab(tab3, "content_type", "内容类型")

# ── Section 3: 问题定位 ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🎯 问题定位与归因摘要")
st.caption("基于当前筛选范围的漏斗数据，自动输出前/后链路判断和策略方向建议")

diagnosis = detect_drop_stage(funnel_summary)
prob_type = diagnosis["problem_type"]
drop_stage = diagnosis["drop_stage"]
drop_rate  = diagnosis["drop_rate"]
summary    = diagnosis["summary"]
details    = diagnosis["details"]
suggestions= diagnosis["suggestion"]

# 颜色编码
type_css = {
    "前链路问题": "front",
    "后链路问题": "back",
    "混合型问题": "mixed",
    "分群差异问题": "",
}
css_cls = type_css.get(prob_type, "")

emoji_map = {
    "前链路问题": "🔴",
    "后链路问题": "🟡",
    "混合型问题": "🟣",
    "分群差异问题": "🔵",
}
emoji = emoji_map.get(prob_type, "⚪")

col_diag, col_action = st.columns([3, 2])

with col_diag:
    st.markdown(f"""
    <div class="diagnosis-card {css_cls}">
        <div style="font-size:1.1rem;font-weight:700;margin-bottom:0.5rem;">
            {emoji} 问题类型：{prob_type}
        </div>
        <div style="font-size:0.9rem;color:#444;margin-bottom:0.8rem;">
            {summary}
        </div>
        <div style="font-size:0.85rem;font-weight:600;color:#1E5799;margin-bottom:0.3rem;">
            📍 重点掉点环节：{drop_stage} = {drop_rate*100:.1f}%
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**详细分析**")
    for d in details:
        st.markdown(f"- {d}")

with col_action:
    st.markdown("**💡 建议策略方向**")
    for i, s in enumerate(suggestions, 1):
        st.markdown(f"""
        <div style="background:#EBF5FB;border-radius:6px;padding:0.6rem 0.8rem;margin-bottom:6px;
                    border-left:3px solid #1E5799;font-size:0.85rem;">
            <b>{i}.</b> {s}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**🔗 下一步建议**")
    st.page_link("pages/3_abtest_designer.py", label="🧪 进入 A/B Test 设计助手", icon="🧪")
    st.page_link("pages/4_ai_review.py",        label="🤖 进入 AI 复盘页",         icon="🤖")

# ── 漏斗各环节转化率横向对比热力图 ──────────────────────────────────────────
st.markdown("---")
with st.expander("📊 展开：流量场景 × 漏斗指标热力图"):
    channel_df = compare_funnel_by_group(df, "channel")
    if not channel_df.empty and len(channel_df) > 1:
        pivot_cols = [m for m in FUNNEL_METRICS if m in channel_df.columns]
        pivot = channel_df.set_index("channel")[pivot_cols]
        from modules.chart_builder import build_heatmap
        fig = build_heatmap(pivot, title="场景 × 漏斗指标热力图", height=300, fmt=".2%")
        st.plotly_chart(fig, use_container_width=True)
