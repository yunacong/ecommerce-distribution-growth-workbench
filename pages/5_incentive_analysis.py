"""
5_incentive_analysis.py — 激励策略效果分析

解决问题：量化优惠券/补贴的真实增量价值，避免"只看GMV涨了多少"的常见误区。
核心方法：有券 vs 无券 CVR/GMV 对比 + 增量 ROI 计算 + 用户分层分析
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys, os
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.data_loader import load_data
from modules.filter_utils import build_filters_from_sidebar, apply_common_filters

st.set_page_config(page_title="激励策略效果分析", page_icon="🎁", layout="wide")

st.markdown("""
<style>
.incentive-card { background:white; border-radius:10px; padding:1.2rem 1.4rem; margin-bottom:0.8rem;
                  box-shadow:0 2px 8px rgba(0,0,0,0.07); border-left:4px solid #1E5799; }
.incentive-card.good { border-left-color:#27AE60; }
.incentive-card.warn { border-left-color:#F39C12; }
.incentive-card.bad  { border-left-color:#E74C3C; }
.metric-highlight { font-size:2rem; font-weight:700; color:#1D3557; }
.roi-positive { color:#27AE60; font-weight:700; }
.roi-negative { color:#E74C3C; font-weight:700; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
## 🎁 激励策略效果分析
<p style="color:#666;font-size:0.93rem;">
激励策略（优惠券/补贴）的核心价值在于<strong>真实增量</strong>，而非表面GMV提升。
本模块通过有券 vs 无券对比、增量ROI计算、用户兴趣鉴别三个维度量化激励效果。
</p>
<hr style="border-color:#E8EDF0;margin-bottom:1.2rem">
""", unsafe_allow_html=True)

# ── 数据加载 ──────────────────────────────────────────────────────────────────
df_full = load_data()
st.sidebar.markdown("## 🎛️ 筛选条件")
filters = build_filters_from_sidebar(df_full, show_experiment=True, date_default_days=30)
df = apply_common_filters(df_full, filters)

if df.empty:
    st.warning("⚠️ 当前筛选条件下无数据，请调整筛选项。")
    st.stop()

st.sidebar.markdown(f"**当前数据量：{len(df):,} 行**")

# ── 数据预处理：有券 / 无券 分组 ─────────────────────────────────────────────
has_coupon_col = "is_subsidy" if "is_subsidy" in df.columns else None

if has_coupon_col:
    df_coupon   = df[df[has_coupon_col] == 1].copy()
    df_no_coupon = df[df[has_coupon_col] == 0].copy()
else:
    # 用 campaign_cost > 0 作为替代判断
    if "campaign_cost" in df.columns:
        df_coupon    = df[df["campaign_cost"] > 0].copy()
        df_no_coupon = df[df["campaign_cost"] == 0].copy()
    else:
        # 随机模拟（演示用）
        np.random.seed(42)
        df = df.copy()
        df["_has_coupon"] = np.random.choice([0, 1], size=len(df), p=[0.55, 0.45])
        df_coupon    = df[df["_has_coupon"] == 1].copy()
        df_no_coupon = df[df["_has_coupon"] == 0].copy()


def calc_group_stats(d):
    """计算某分组的核心指标"""
    n_imp = (d["event_type"] == "impression").sum() if "event_type" in d.columns else len(d)
    n_click = (d["event_type"] == "click").sum() if "event_type" in d.columns else 0
    n_pay  = (d["event_type"] == "pay").sum() if "event_type" in d.columns else 0
    gmv    = d.loc[d["event_type"] == "pay", "order_amount"].sum() if "order_amount" in d.columns else 0
    cost   = d["campaign_cost"].sum() if "campaign_cost" in d.columns else 0
    ctr    = n_click / n_imp if n_imp > 0 else 0
    cvr    = n_pay / n_imp if n_imp > 0 else 0
    aov    = gmv / n_pay if n_pay > 0 else 0
    return {
        "impression": n_imp, "click": n_click, "pay": n_pay,
        "gmv": gmv, "cost": cost, "ctr": ctr, "cvr": cvr, "aov": aov
    }


stats_coupon    = calc_group_stats(df_coupon)
stats_no_coupon = calc_group_stats(df_no_coupon)

# ══════════════════════════════════════════════════════════════════════════════
# Section 1: 核心指标对比
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 📊 有券 vs 无券：核心指标对比")

col1, col2, col3, col4 = st.columns(4)

def delta_badge(val_a, val_b, higher_is_better=True):
    """返回差值和颜色"""
    if val_b == 0:
        return "N/A", "gray"
    delta = (val_a - val_b) / val_b
    color = "#27AE60" if (delta > 0) == higher_is_better else "#E74C3C"
    sign  = "+" if delta > 0 else ""
    return f"{sign}{delta*100:.1f}%", color

metrics_compare = [
    ("CTR 点击率",    stats_coupon["ctr"],    stats_no_coupon["ctr"],    True,  ".2%"),
    ("CVR 转化率",    stats_coupon["cvr"],    stats_no_coupon["cvr"],    True,  ".2%"),
    ("客单价 AOV",    stats_coupon["aov"],    stats_no_coupon["aov"],    True,  ",.0f"),
    ("支付用户数",    stats_coupon["pay"],    stats_no_coupon["pay"],    True,  ",.0f"),
]

for col, (label, val_c, val_nc, hib, fmt) in zip([col1, col2, col3, col4], metrics_compare):
    d_str, d_color = delta_badge(val_c, val_nc, hib)
    fmt_fn = (lambda v, f=fmt: f"¥{v:{f}}" if "f" in f or f == ",.0f" else f"{v:{f}}")
    with col:
        st.markdown(f"""
        <div class="incentive-card">
            <div style="font-size:0.78rem;color:#888;margin-bottom:4px;">🎫 {label}</div>
            <div style="font-size:0.9rem;color:#555;">有券：<b>{val_c:{fmt}}</b></div>
            <div style="font-size:0.9rem;color:#555;">无券：<b>{val_nc:{fmt}}</b></div>
            <div style="font-size:1rem;font-weight:700;color:{d_color};margin-top:4px;">
                有券 vs 无券：{d_str}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── 对比柱状图 ────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
compare_df = pd.DataFrame({
    "指标": ["CTR", "CVR", "CTR", "CVR"],
    "数值": [
        stats_coupon["ctr"] * 100, stats_coupon["cvr"] * 100,
        stats_no_coupon["ctr"] * 100, stats_no_coupon["cvr"] * 100
    ],
    "分组": ["有券", "有券", "无券", "无券"]
})

fig_compare = px.bar(
    compare_df, x="指标", y="数值", color="分组",
    barmode="group",
    color_discrete_map={"有券": "#1E5799", "无券": "#AED6F1"},
    title="有券 vs 无券：CTR / CVR 对比（%）",
    labels={"数值": "转化率（%）"},
    height=350,
    text_auto=".2f"
)
fig_compare.update_layout(plot_bgcolor="white", margin=dict(t=40, b=30))
st.plotly_chart(fig_compare, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# Section 2: 增量 ROI 计算
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 💰 增量 ROI 计算")
st.markdown("""
<p style="color:#666;font-size:0.88rem;">
<b>增量GMV</b> = 有券组GMV - 无券组（按比例缩放的基准GMV）；只有增量GMV > 优惠成本，ROI才算合格。
</p>
""", unsafe_allow_html=True)

col_roi_input, col_roi_result = st.columns([1, 1])

with col_roi_input:
    st.markdown("#### ⚙️ 参数调整")
    platform_take_rate = st.slider("平台佣金率（%）", 1, 20, 5,
                                    help="平台从GMV中抽取的佣金比例") / 100
    coupon_cost_override = st.number_input(
        "优惠券总成本（元，0=使用数据中campaign_cost）",
        min_value=0.0, value=0.0, step=1000.0,
        help="若设为0，自动使用数据字段中的 campaign_cost 总和"
    )
    baseline_scale = stats_coupon["impression"] / max(stats_no_coupon["impression"], 1)

    actual_cost = coupon_cost_override if coupon_cost_override > 0 else stats_coupon["cost"]
    baseline_gmv_scaled = stats_no_coupon["gmv"] * baseline_scale
    incremental_gmv = max(stats_coupon["gmv"] - baseline_gmv_scaled, 0)
    incremental_revenue = incremental_gmv * platform_take_rate
    roi = incremental_revenue / actual_cost if actual_cost > 0 else float("inf")

with col_roi_result:
    st.markdown("#### 📊 ROI 计算结果")
    roi_color = "good" if roi >= 1.0 else "bad"
    roi_verdict = "✅ ROI 合格，激励策略具有正收益" if roi >= 1.0 else "❌ ROI 不合格，成本超过增量收益"

    st.markdown(f"""
    <div class="incentive-card {roi_color}">
        <div style="font-size:0.9rem;color:#555;margin-bottom:8px;">{roi_verdict}</div>
        <table style="width:100%;font-size:0.85rem;border-collapse:collapse;">
            <tr><td style="padding:3px 6px;color:#666;">有券组 GMV</td>
                <td style="text-align:right;font-weight:600;">¥{stats_coupon['gmv']:,.0f}</td></tr>
            <tr><td style="padding:3px 6px;color:#666;">无券组基准 GMV（等比缩放）</td>
                <td style="text-align:right;font-weight:600;">¥{baseline_gmv_scaled:,.0f}</td></tr>
            <tr style="background:#EBF5FB;"><td style="padding:3px 6px;"><b>增量 GMV</b></td>
                <td style="text-align:right;font-weight:700;">¥{incremental_gmv:,.0f}</td></tr>
            <tr><td style="padding:3px 6px;color:#666;">平台增量佣金收入</td>
                <td style="text-align:right;">¥{incremental_revenue:,.0f}</td></tr>
            <tr><td style="padding:3px 6px;color:#666;">优惠成本</td>
                <td style="text-align:right;">¥{actual_cost:,.0f}</td></tr>
            <tr style="background:{'#EAFAF1' if roi >= 1 else '#FDEDEC'};"><td style="padding:3px 6px;"><b>增量 ROI</b></td>
                <td style="text-align:right;font-size:1.2rem;font-weight:700;
                    color:{'#27AE60' if roi >= 1 else '#E74C3C'};">{roi:.2f}x</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

# ROI 可视化：瀑布图
fig_roi = go.Figure(go.Waterfall(
    name="ROI分解", orientation="v",
    measure=["absolute", "absolute", "relative", "relative", "total"],
    x=["有券GMV", "无券基准GMV", "增量GMV", "优惠成本", "净增量"],
    y=[stats_coupon["gmv"], -baseline_gmv_scaled, incremental_gmv, -actual_cost,
       incremental_gmv - actual_cost],
    connector={"line": {"color": "rgb(63, 63, 63)"}},
    decreasing={"marker": {"color": "#E74C3C"}},
    increasing={"marker": {"color": "#27AE60"}},
    totals={"marker": {"color": "#1E5799"}},
    text=[f"¥{v/10000:.1f}万" for v in [stats_coupon["gmv"], -baseline_gmv_scaled,
                                          incremental_gmv, -actual_cost,
                                          incremental_gmv - actual_cost]],
    textposition="outside"
))
fig_roi.update_layout(
    title="增量GMV 瀑布图分解",
    height=380, plot_bgcolor="white",
    margin=dict(t=40, b=30),
    yaxis_title="金额（元）"
)
st.plotly_chart(fig_roi, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# Section 3: 用户分层分析（兴趣鉴别）
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 👥 用户分层：兴趣鉴别分析")
st.markdown("""
<p style="color:#666;font-size:0.88rem;">
激励策略最大风险是"薅羊毛用户"：领券后购买，无券则流失，对平台贡献增量为零。
需要识别哪些用户是真正的<b>增量用户</b>，哪些只是<b>价格敏感用户</b>。
</p>
""", unsafe_allow_html=True)

if "user_type" in df.columns:
    user_grp = df.groupby(["user_type"]).agg(
        impression=("event_type", lambda x: (x == "impression").sum()),
        pay=("event_type", lambda x: (x == "pay").sum()),
        gmv=("order_amount", "sum") if "order_amount" in df.columns else ("event_type", "count"),
    ).reset_index()
    user_grp["cvr"] = user_grp["pay"] / user_grp["impression"].replace(0, np.nan)

    fig_user = px.bar(
        user_grp, x="user_type", y="cvr",
        color="user_type",
        title="不同用户类型的 CVR（有无激励策略拆分）",
        labels={"cvr": "CVR（支付/曝光）", "user_type": "用户类型"},
        height=340,
        text_auto=".2%"
    )
    fig_user.update_layout(plot_bgcolor="white", showlegend=False)
    st.plotly_chart(fig_user, use_container_width=True)

# 用户分层建议表
st.markdown("#### 🎯 分层激励策略建议")
segment_data = {
    "用户类型": ["刚性购买用户", "价格敏感用户", "寻找优惠用户", "沉默召回用户"],
    "行为特征": [
        "无论有无优惠都会购买",
        "有优惠才转化，无优惠流失",
        "专门搜寻并等待优惠",
        "长期未活跃，优惠可召回"
    ],
    "增量贡献": ["⭕ 零增量（已有购买意愿）", "✅ 高增量（价格是决策因素）",
                 "❌ 负增量（只占便宜不留存）", "✅ 中增量（有效召回）"],
    "建议策略": [
        "不发券，节省成本",
        "发小额精准券，控制力度",
        "限制领券频次，防薅羊毛",
        "发专属召回券，监控次月留存"
    ],
}
st.dataframe(pd.DataFrame(segment_data), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# Section 4: SQL 查看器
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🖥️ 查看背后的 SQL（DuckDB）")

isql1, isql2 = st.tabs(["有券 vs 无券对比", "增量 ROI 计算"])

with isql1:
    st.code("""
-- 有券 vs 无券 核心指标对比
SELECT
    is_subsidy AS has_coupon,
    COUNT(DISTINCT user_id)                                                  AS users,
    SUM(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END)              AS impressions,
    SUM(CASE WHEN event_type = 'click'      THEN 1 ELSE 0 END)              AS clicks,
    SUM(CASE WHEN event_type = 'pay'        THEN 1 ELSE 0 END)              AS payments,
    ROUND(1.0 * SUM(CASE WHEN event_type='click' THEN 1 ELSE 0 END)
               / NULLIF(SUM(CASE WHEN event_type='impression' THEN 1 ELSE 0 END),0),4) AS ctr,
    ROUND(1.0 * SUM(CASE WHEN event_type='pay' THEN 1 ELSE 0 END)
               / NULLIF(SUM(CASE WHEN event_type='impression' THEN 1 ELSE 0 END),0),4) AS cvr,
    SUM(CASE WHEN event_type='pay' THEN order_amount ELSE 0 END)            AS gmv,
    SUM(campaign_cost)                                                       AS total_cost,
    ROUND(SUM(CASE WHEN event_type='pay' THEN order_amount ELSE 0 END)
         / NULLIF(SUM(campaign_cost),0), 2)                                 AS surface_roi
FROM distribution_events
WHERE event_time BETWEEN :start_date AND :end_date
GROUP BY is_subsidy;
""", language="sql")

with isql2:
    st.code("""
-- 增量 ROI 计算（对比有券/无券GMV，估算真实增量）
WITH group_stats AS (
    SELECT
        is_subsidy,
        SUM(CASE WHEN event_type='impression' THEN 1 ELSE 0 END) AS impressions,
        SUM(CASE WHEN event_type='pay' THEN order_amount ELSE 0 END) AS gmv,
        SUM(campaign_cost) AS cost
    FROM distribution_events
    WHERE event_time BETWEEN :start_date AND :end_date
    GROUP BY is_subsidy
),
coupon_stats    AS (SELECT * FROM group_stats WHERE is_subsidy = 1),
no_coupon_stats AS (SELECT * FROM group_stats WHERE is_subsidy = 0),
incremental AS (
    SELECT
        c.gmv AS coupon_gmv,
        -- 无券 GMV 按曝光比例缩放（控制流量差异）
        nc.gmv * (c.impressions * 1.0 / nc.impressions) AS baseline_gmv_scaled,
        c.gmv - nc.gmv * (c.impressions * 1.0 / nc.impressions) AS incremental_gmv,
        c.cost AS coupon_cost,
        0.05   AS platform_take_rate
    FROM coupon_stats c CROSS JOIN no_coupon_stats nc
)
SELECT
    coupon_gmv,
    baseline_gmv_scaled,
    incremental_gmv,
    coupon_cost,
    incremental_gmv * platform_take_rate                           AS incremental_revenue,
    ROUND((incremental_gmv * platform_take_rate) / coupon_cost, 2) AS incremental_roi
FROM incremental;
""", language="sql")

# 侧边栏
st.sidebar.markdown("""
## 📖 激励分析说明

**增量 ROI 计算逻辑**

```
增量GMV = 有券GMV - 无券GMV（等比缩放）
增量收入 = 增量GMV × 平台佣金率
增量ROI = 增量收入 / 优惠成本
```

**ROI 判断标准**
- ROI > 1.5x → 优秀，可扩大力度
- ROI 1.0-1.5x → 合格，维持策略
- ROI < 1.0x → 亏损，需降低力度

**常见风险**
- 刚性用户占比过高 → 成本浪费
- 薅羊毛用户激增 → 风控介入
- 新奇效应 → 等待效果稳定
""")
