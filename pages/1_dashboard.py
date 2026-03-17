"""
1_dashboard.py — 策略总览 Dashboard

解决问题：快速感知当前业务整体状态，识别 CTR/CVR/GMV 异常场景，
          为后续漏斗分析和实验设计提供入口。
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.data_loader import load_data
from modules.filter_utils import build_filters_from_sidebar, apply_common_filters
from modules.metric_calculator import calc_core_metrics, calc_trend_metrics, calc_group_metrics, calc_period_comparison
from modules.chart_builder import (
    build_trend_line_chart, build_metric_bar_chart,
    build_grouped_bar_chart, DANGER, SUCCESS, WARNING, PRIMARY
)

st.set_page_config(page_title="策略总览 Dashboard", page_icon="📊", layout="wide")

# ── 全局样式复用 ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card { background:white; border-radius:12px; padding:1.1rem; box-shadow:0 2px 8px rgba(0,0,0,0.07); border-left:4px solid #1E5799; }
.metric-card.danger { border-left-color:#E74C3C; }
.metric-card.success { border-left-color:#27AE60; }
.metric-card.warning { border-left-color:#F39C12; }
.anomaly-box { background:#FDEDEC; border:1px solid #F5B7B1; border-radius:8px; padding:1rem 1.2rem; margin:0.5rem 0; }
.normal-box  { background:#EAFAF1; border:1px solid #A9DFBF;  border-radius:8px; padding:1rem 1.2rem; margin:0.5rem 0; }
.info-box    { background:#EBF5FB; border:1px solid #AED6F1;  border-radius:8px; padding:1rem 1.2rem; margin:0.5rem 0; }
</style>
""", unsafe_allow_html=True)

# ── 页面标题 ──────────────────────────────────────────────────────────────────
st.markdown("""
## 📊 策略总览 Dashboard
<p style="color:#666;font-size:0.93rem;">
本页面用于查看整体业务基线、近期趋势变化及不同场景/人群/内容类型的核心指标表现。
发现异常后可进入漏斗分析页定位问题，或进入 A/B Test 页设计验证方案。
</p>
<hr style="border-color:#E8EDF0;margin-bottom:1.2rem">
""", unsafe_allow_html=True)

# ── 数据加载 ──────────────────────────────────────────────────────────────────
with st.spinner("加载数据中..."):
    df_full = load_data()

# ── 侧边栏筛选 ────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🎛️ 筛选条件")
filters = build_filters_from_sidebar(df_full, show_experiment=True, date_default_days=30)

df = apply_common_filters(df_full, filters)
n_rows = len(df)

if n_rows == 0:
    st.warning("⚠️ 当前筛选条件下无数据，请调整筛选项。")
    st.stop()

st.sidebar.markdown(f"**当前数据量：{n_rows:,} 行**")

# ── 核心指标卡片 ──────────────────────────────────────────────────────────────
metrics = calc_core_metrics(df)
comparison = calc_period_comparison(df_full, filters, days=14)
global_m = calc_core_metrics(df_full)

def delta_str(key: str) -> str:
    if key not in comparison:
        return ""
    chg = comparison[key]["change_pct"]
    sign = "+" if chg >= 0 else ""
    return f"{sign}{chg*100:.1f}%"

def card_class(key: str, value: float, threshold_ratio: float = 0.9) -> str:
    global_val = global_m.get(key, 0)
    if global_val == 0:
        return ""
    if value < global_val * threshold_ratio:
        return "danger"
    if value > global_val * 1.05:
        return "success"
    return ""

st.markdown("### 📌 核心指标概览")
c1, c2, c3, c4, c5 = st.columns(5)

for col, key, label, fmt_fn, unit, threshold in [
    (c1, "ctr",           "CTR 点击率",       lambda v: f"{v*100:.2f}%",       "",  0.9),
    (c2, "cvr",           "CVR 综合转化率",    lambda v: f"{v*100:.2f}%",       "",  0.9),
    (c3, "gmv",           "GMV 成交金额",      lambda v: f"¥{v/10000:.1f}万",  "",  0.95),
    (c4, "new_user_rate", "新客率",            lambda v: f"{v*100:.1f}%",       "",  0.85),
    (c5, "roi",           "ROI 投资回报",      lambda v: f"{v:.2f}x",           "",  0.8),
]:
    val = metrics.get(key, 0)
    cls = card_class(key, val, threshold)
    delta = delta_str(key)
    with col:
        badge = "🔴" if cls == "danger" else ("🟢" if cls == "success" else "🔵")
        delta_color = "red" if delta.startswith("-") and key in ["ctr","cvr","gmv","roi"] else "green"
        st.markdown(f"""
        <div class="metric-card {cls}">
            <div style="font-size:0.78rem;color:#888;margin-bottom:4px;">{badge} {label}</div>
            <div style="font-size:1.7rem;font-weight:700;color:#1D3557;">{fmt_fn(val)}</div>
            <div style="font-size:0.8rem;color:{'#E74C3C' if delta.startswith('-') else '#27AE60'};">
                环比 {delta if delta else 'N/A'}
            </div>
            <div style="font-size:0.72rem;color:#aaa;margin-top:2px;">
                全局均值：{fmt_fn(global_m.get(key, 0))}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 趋势图区 ──────────────────────────────────────────────────────────────────
trend_df = calc_trend_metrics(df)
st.markdown("### 📈 核心指标趋势")

tab_t1, tab_t2, tab_t3 = st.tabs(["CTR & CVR 双轴趋势", "GMV 日趋势", "ROI & 新客率趋势"])

with tab_t1:
    if not trend_df.empty:
        fig = build_trend_line_chart(
            trend_df, x="event_date", y_cols=["ctr", "cvr"],
            y_labels={"ctr": "CTR 点击率", "cvr": "CVR 转化率"},
            title="CTR / CVR 双指标趋势",
            height=340, y_format="percent"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("数据不足，无法展示趋势图。")

with tab_t2:
    if not trend_df.empty:
        fig = build_trend_line_chart(
            trend_df, x="event_date", y_cols=["gmv"],
            y_labels={"gmv": "GMV（元）"},
            title="GMV 日趋势",
            height=340, y_format="currency"
        )
        st.plotly_chart(fig, use_container_width=True)

with tab_t3:
    if not trend_df.empty:
        fig = build_trend_line_chart(
            trend_df, x="event_date", y_cols=["roi", "new_user_rate"],
            y_labels={"roi": "ROI", "new_user_rate": "新客率"},
            title="ROI & 新客率趋势",
            height=340, y_format="number"
        )
        st.plotly_chart(fig, use_container_width=True)

# ── 结构对比区 ────────────────────────────────────────────────────────────────
st.markdown("### 📊 结构对比分析")
st.caption("从场景、人群、内容类型、商品类目多维度快速识别效率差异")

tab1, tab2, tab3, tab4 = st.tabs(["📡 按流量场景", "👤 按用户类型", "🎬 按内容类型", "🛍️按商品类目"])

metric_opts = {"CTR 点击率": "ctr", "CVR 转化率": "cvr",
               "GMV（万元）": "gmv", "ROI": "roi"}

for tab, group_col, label in [
    (tab1, "channel",       "流量场景"),
    (tab2, "user_type",     "用户类型"),
    (tab3, "content_type",  "内容类型"),
    (tab4, "item_category", "商品类目"),
]:
    with tab:
        group_df = calc_group_metrics(df, [group_col])
        if group_df.empty:
            st.info("数据不足")
            continue

        sel_metric_label = st.selectbox(
            f"选择指标（{label}维度）",
            list(metric_opts.keys()),
            key=f"metric_{group_col}"
        )
        sel_metric = metric_opts[sel_metric_label]

        # 格式化 gmv 为万元
        plot_df = group_df.copy()
        if sel_metric == "gmv":
            plot_df["gmv"] = plot_df["gmv"] / 10000

        y_fmt = "percent" if sel_metric in ["ctr","cvr"] else "number"
        global_avg = global_m.get(sel_metric, None)
        if sel_metric == "gmv" and global_avg:
            global_avg = global_avg / 10000

        fig = build_metric_bar_chart(
            plot_df, x=group_col, y=sel_metric,
            title=f"{label} × {sel_metric_label}",
            height=340,
            y_format=y_fmt,
            global_avg=global_avg,
        )
        st.plotly_chart(fig, use_container_width=True)

        # 展示明细表格
        display_cols = [group_col, "impression", "click", "pay", "ctr", "cvr", "gmv", "roi"]
        display_cols = [c for c in display_cols if c in group_df.columns]
        display_df = group_df[display_cols].copy()
        for col in ["ctr", "cvr"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].map(lambda x: f"{x*100:.2f}%")
        if "gmv" in display_df.columns:
            display_df["gmv"] = display_df["gmv"].map(lambda x: f"¥{x/10000:.1f}万")
        if "roi" in display_df.columns:
            display_df["roi"] = display_df["roi"].map(lambda x: f"{x:.2f}x")

        with st.expander(f"展开查看 {label} 明细数据"):
            st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── 异常提示区 ────────────────────────────────────────────────────────────────
st.markdown("### ⚡ 异常识别与下一步建议")

ctr_val  = metrics.get("ctr",  0)
cvr_val  = metrics.get("cvr",  0)
gmv_val  = metrics.get("gmv",  0)
roi_val  = metrics.get("roi",  0)
g_ctr    = global_m.get("ctr", 0)
g_cvr    = global_m.get("cvr", 0)
g_roi    = global_m.get("roi", 0)

anomalies = []
if ctr_val < g_ctr * 0.9:
    anomalies.append(f"🔴 **CTR 偏低**：当前 {ctr_val*100:.2f}%，低于全局均值 {g_ctr*100:.2f}% 约 {abs(ctr_val/g_ctr-1)*100:.1f}%，前链路点击效率不足。")
if cvr_val < g_cvr * 0.9:
    anomalies.append(f"🔴 **CVR 偏低**：当前 {cvr_val*100:.2f}%，低于全局均值 {g_cvr*100:.2f}% 约 {abs(cvr_val/g_cvr-1)*100:.1f}%，后链路转化承接不足。")
if roi_val < 1.0:
    anomalies.append(f"🔴 **ROI < 1.0**：当前 ROI = {roi_val:.2f}x，策略成本回收效率偏低，需关注成本控制。")
if metrics.get("new_user_rate", 0) < 0.15:
    anomalies.append(f"🟡 **新客率偏低**：当前新客率 {metrics.get('new_user_rate',0)*100:.1f}%，低于 15% 基准线，新客获取效果有待提升。")

if anomalies:
    with st.container():
        st.markdown('<div class="anomaly-box">', unsafe_allow_html=True)
        st.markdown("#### 🚨 发现以下异常，建议重点关注")
        for a in anomalies:
            st.markdown(a)
        st.markdown("</div>", unsafe_allow_html=True)

    # 问题判断
    is_front = ctr_val < g_ctr * 0.9
    is_back  = cvr_val < g_cvr * 0.9

    if is_front and is_back:
        prob_type = "**混合型问题**：前后链路均存在效率损失"
        suggestion = "建议先进入**漏斗分析页**确认重点掉点环节，再针对性设计 A/B 实验。"
    elif is_front:
        prob_type = "**前链路问题**：CTR 偏低，曝光转化效率不足"
        suggestion = "建议优先进入**漏斗分析页**拆解各场景和内容类型的点击转化，设计展示优化或排序调整实验。"
    elif is_back:
        prob_type = "**后链路问题**：CVR 偏低，点击后承接转化不足"
        suggestion = "建议优先进入**漏斗分析页**查看加购、下单、支付环节，设计详情优化或激励策略实验。"
    else:
        prob_type = "**收益质量问题**：ROI 或成本指标需关注"
        suggestion = "建议结合实验组数据，在**AI 复盘页**生成成本控制策略建议。"

    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.info(f"**问题判断**：{prob_type}\n\n{suggestion}")
    with col_r:
        st.markdown("**🔗 快捷跳转**")
        st.page_link("pages/2_funnel_analysis.py", label="🔍 进入漏斗分析页", icon="🔍")
        st.page_link("pages/3_abtest_designer.py", label="🧪 进入 A/B Test 设计", icon="🧪")
        st.page_link("pages/4_ai_review.py",        label="🤖 进入 AI 复盘页",   icon="🤖")
else:
    st.markdown('<div class="normal-box">', unsafe_allow_html=True)
    st.markdown(f"""
    #### ✅ 当前指标表现正常
    - CTR：{ctr_val*100:.2f}%（全局均值 {g_ctr*100:.2f}%）
    - CVR：{cvr_val*100:.2f}%（全局均值 {g_cvr*100:.2f}%）
    - ROI：{roi_val:.2f}x

    整体指标处于正常区间。建议继续观察趋势变化，或进行分群拆解以寻找优化机会点。
    """)
    st.markdown("</div>", unsafe_allow_html=True)
    st.info("💡 **建议**：整体表现良好时，可深入拆解分群差异，寻找高收益人群和场景进行重点投入。")

# ── SQL 查看器 ────────────────────────────────────────────────────────────────
st.markdown("### 🖥️ 查看背后的 SQL（DuckDB）")
st.caption("所有图表均由以下 SQL 计算驱动，可复制到任意支持 DuckDB / 标准 SQL 的环境执行")

sql_tab1, sql_tab2, sql_tab3, sql_tab4 = st.tabs(["核心指标", "趋势分析", "分组对比", "实验组对比"])

with sql_tab1:
    st.code("""
-- 核心指标汇总（当前筛选条件下）
SELECT
    COUNT(DISTINCT CASE WHEN event_type = 'impression' THEN user_id END)   AS impression_uv,
    COUNT(DISTINCT CASE WHEN event_type = 'click'      THEN user_id END)   AS click_uv,
    COUNT(DISTINCT CASE WHEN event_type = 'pay'        THEN user_id END)   AS pay_uv,
    ROUND(1.0 * SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END)
               / NULLIF(SUM(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END), 0), 4) AS ctr,
    ROUND(1.0 * SUM(CASE WHEN event_type = 'pay' THEN 1 ELSE 0 END)
               / NULLIF(SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END), 0), 4)    AS cvr,
    SUM(CASE WHEN event_type = 'pay' THEN order_amount ELSE 0 END)         AS gmv,
    ROUND(SUM(CASE WHEN event_type = 'pay' THEN order_amount ELSE 0 END)
         / NULLIF(SUM(campaign_cost), 0), 2)                               AS roi
FROM distribution_events
WHERE event_time BETWEEN :start_date AND :end_date
  AND channel        = :channel        -- 'all' 则不过滤
  AND user_type      = :user_type      -- 'all' 则不过滤
  AND experiment_group IN (:groups);
""", language="sql")

with sql_tab2:
    st.code("""
-- 核心指标日趋势
SELECT
    DATE(event_time)  AS event_date,
    ROUND(1.0 * SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END)
               / NULLIF(SUM(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END), 0), 4) AS ctr,
    ROUND(1.0 * SUM(CASE WHEN event_type = 'pay' THEN 1 ELSE 0 END)
               / NULLIF(SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END), 0), 4)    AS cvr,
    SUM(CASE WHEN event_type = 'pay' THEN order_amount ELSE 0 END)         AS gmv,
    ROUND(SUM(CASE WHEN event_type = 'pay' THEN order_amount ELSE 0 END)
         / NULLIF(SUM(campaign_cost), 0), 2)                               AS roi,
    ROUND(1.0 * SUM(CASE WHEN is_new_payer = 1 THEN 1 ELSE 0 END)
               / NULLIF(SUM(CASE WHEN event_type = 'pay' THEN 1 ELSE 0 END), 0), 4)      AS new_user_rate
FROM distribution_events
WHERE event_time BETWEEN :start_date AND :end_date
GROUP BY DATE(event_time)
ORDER BY event_date;
""", language="sql")

with sql_tab3:
    st.code("""
-- 多维度结构对比（以 channel 为例，替换 channel 字段可切换维度）
SELECT
    channel,
    SUM(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END) AS impression,
    SUM(CASE WHEN event_type = 'click'      THEN 1 ELSE 0 END) AS click,
    SUM(CASE WHEN event_type = 'pay'        THEN 1 ELSE 0 END) AS pay,
    ROUND(1.0 * SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END)
               / NULLIF(SUM(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END), 0), 4) AS ctr,
    ROUND(1.0 * SUM(CASE WHEN event_type = 'pay' THEN 1 ELSE 0 END)
               / NULLIF(SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END), 0), 4)    AS cvr,
    SUM(CASE WHEN event_type = 'pay' THEN order_amount ELSE 0 END)         AS gmv,
    ROUND(SUM(CASE WHEN event_type = 'pay' THEN order_amount ELSE 0 END)
         / NULLIF(SUM(campaign_cost), 0), 2)                               AS roi
FROM distribution_events
WHERE event_time BETWEEN :start_date AND :end_date
GROUP BY channel
ORDER BY gmv DESC;
-- 可替换 channel 为：user_type / content_type / item_category / price_band
""", language="sql")

with sql_tab4:
    st.code("""
-- A/B 实验组对比（控制组 vs 实验组）
SELECT
    experiment_group,
    COUNT(DISTINCT user_id)                                                 AS total_users,
    SUM(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END)             AS impressions,
    SUM(CASE WHEN event_type = 'click'      THEN 1 ELSE 0 END)             AS clicks,
    SUM(CASE WHEN event_type = 'pay'        THEN 1 ELSE 0 END)             AS payments,
    ROUND(1.0 * SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END)
               / NULLIF(SUM(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END), 0), 4) AS ctr,
    ROUND(1.0 * SUM(CASE WHEN event_type = 'pay' THEN 1 ELSE 0 END)
               / NULLIF(SUM(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END), 0), 4) AS cvr,
    SUM(CASE WHEN event_type = 'pay' THEN order_amount ELSE 0 END)         AS gmv,
    ROUND(SUM(CASE WHEN event_type = 'pay' THEN order_amount ELSE 0 END)
         / NULLIF(SUM(campaign_cost), 0), 2)                               AS roi
FROM distribution_events
WHERE event_time BETWEEN :start_date AND :end_date
GROUP BY experiment_group
ORDER BY experiment_group;
""", language="sql")

# ── 底部风险提醒 ──────────────────────────────────────────────────────────────
with st.expander("⚠️ 使用说明与风险提醒"):
    st.markdown("""
    - **数据范围**：当前展示数据基于所选筛选条件，结论不应直接外推至全量场景
    - **环比计算**：基于相同时间长度的上一周期对比，若历史数据不足则显示 N/A
    - **异常判断**：CTR/CVR 低于全局均值 10% 触发红色预警，ROI < 1.0 触发预警
    - **指标口径**：CTR = Click/Impression；CVR = Pay/Click；ROI = GMV/Campaign Cost
    """)
