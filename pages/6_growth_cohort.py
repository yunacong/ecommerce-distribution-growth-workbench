"""
6_growth_cohort.py — 用户增长与 Cohort 留存分析

解决问题：从 AARRR 增长框架角度量化用户全生命周期价值，
          通过 Cohort 留存热力图识别不同批次用户的留存差异，
          结合新老用户对比指导精细化增长策略。
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.data_loader import load_data
from modules.filter_utils import build_filters_from_sidebar, apply_common_filters

st.set_page_config(page_title="用户增长与 Cohort 分析", page_icon="📈", layout="wide")

st.markdown("""
<style>
.growth-card { background:white; border-radius:10px; padding:1.1rem 1.3rem; margin-bottom:0.8rem;
               box-shadow:0 2px 8px rgba(0,0,0,0.07); border-top:3px solid #1E5799; }
.aarrr-badge { display:inline-block; border-radius:6px; padding:4px 12px; font-size:0.82rem;
               font-weight:600; margin:3px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
## 📈 用户增长与 Cohort 留存分析
<p style="color:#666;font-size:0.93rem;">
基于 AARRR 增长框架，量化各阶段用户转化漏斗；通过 Cohort 留存热力图追踪不同批次用户的粘性表现；
对比新老用户行为差异，指导精细化增长策略制定。
</p>
<hr style="border-color:#E8EDF0;margin-bottom:1.2rem">
""", unsafe_allow_html=True)

# ── 数据加载 ──────────────────────────────────────────────────────────────────
df_full = load_data()
st.sidebar.markdown("## 🎛️ 筛选条件")
filters = build_filters_from_sidebar(df_full, show_experiment=False, date_default_days=60)
df = apply_common_filters(df_full, filters)

if df.empty:
    st.warning("⚠️ 无数据，请调整筛选条件。")
    st.stop()

st.sidebar.markdown(f"**当前数据量：{len(df):,} 行**")

# ── 工具函数 ──────────────────────────────────────────────────────────────────
def safe_rate(a, b):
    return a / b if b > 0 else 0


# ══════════════════════════════════════════════════════════════════════════════
# Section 1: AARRR 增长指标看板
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🚀 AARRR 增长指标全景")

# 计算各阶段指标
total_users   = df["user_id"].nunique() if "user_id" in df.columns else len(df)
imp_users     = df.loc[df["event_type"] == "impression", "user_id"].nunique() if "event_type" in df.columns else total_users
click_users   = df.loc[df["event_type"] == "click", "user_id"].nunique() if "event_type" in df.columns else 0
pay_users     = df.loc[df["event_type"] == "pay", "user_id"].nunique() if "event_type" in df.columns else 0
new_users     = df.loc[(df["event_type"] == "pay") & (df.get("is_new_payer", pd.Series(0)) == 1), "user_id"].nunique() if "is_new_payer" in df.columns else int(pay_users * 0.35)
gmv_total     = df.loc[df["event_type"] == "pay", "order_amount"].sum() if "order_amount" in df.columns else 0

# AARRR 指标卡
aarrr_cols = st.columns(5)
aarrr_data = [
    ("Acquisition\n获客", f"{imp_users:,}", "曝光触达用户", "#1E5799"),
    ("Activation\n激活", f"{click_users:,}", f"点击激活\n激活率 {safe_rate(click_users, imp_users):.1%}", "#2E86AB"),
    ("Retention\n留存", "—", "见 Cohort 热力图↓", "#27AE60"),
    ("Revenue\n变现", f"¥{gmv_total/10000:.0f}万", f"支付用户 {pay_users:,}", "#F39C12"),
    ("Referral\n传播", f"{safe_rate(new_users, pay_users):.1%}", "新客占比（分享效果替代）", "#9B59B6"),
]

for col, (stage, value, subtitle, color) in zip(aarrr_cols, aarrr_data):
    with col:
        st.markdown(f"""
        <div class="growth-card" style="border-top-color:{color};">
            <div style="font-size:0.72rem;color:#888;white-space:pre-line;">{stage}</div>
            <div style="font-size:1.5rem;font-weight:700;color:#1D3557;">{value}</div>
            <div style="font-size:0.75rem;color:#666;white-space:pre-line;">{subtitle}</div>
        </div>
        """, unsafe_allow_html=True)

# AARRR 漏斗图
aarrr_fig = go.Figure(go.Funnel(
    y=["曝光触达（Acquisition）", "点击激活（Activation）", "支付转化（Revenue）", "新客获取（Referral）"],
    x=[imp_users, click_users, pay_users, new_users],
    textinfo="value+percent initial",
    marker=dict(color=["#1E5799", "#2E86AB", "#F39C12", "#9B59B6"]),
    connector=dict(line=dict(color="#E8EDF0", width=2, dash="dot")),
))
aarrr_fig.update_layout(
    title="AARRR 增长漏斗（用户数）",
    height=360, margin=dict(t=40, b=20, l=20, r=20),
    plot_bgcolor="white"
)
st.plotly_chart(aarrr_fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# Section 2: Cohort 留存热力图
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🗓️ Cohort 留存分析")
st.markdown("""
<p style="color:#666;font-size:0.88rem;">
按用户首次支付月份分群（Cohort），追踪该批用户在后续各月的活跃留存情况。
热力图颜色越深 = 留存率越高。
</p>
""", unsafe_allow_html=True)

# 构建 Cohort 数据（基于支付行为）
if "event_type" in df.columns and "order_amount" in df.columns and "event_time" in df.columns:
    df_pay = df[df["event_type"] == "pay"].copy()
    df_pay["event_time"] = pd.to_datetime(df_pay["event_time"])
    df_pay["month"] = df_pay["event_time"].dt.to_period("M")

    if "user_id" in df_pay.columns:
        # 首次支付月 = Cohort 月
        first_pay = df_pay.groupby("user_id")["month"].min().reset_index()
        first_pay.columns = ["user_id", "cohort_month"]
        df_cohort = df_pay.merge(first_pay, on="user_id")
        df_cohort["period_number"] = (
            df_cohort["month"].astype(int) - df_cohort["cohort_month"].astype(int)
        )

        # 每个 cohort_month × period_number 的活跃用户数
        cohort_pivot = df_cohort.groupby(["cohort_month", "period_number"])["user_id"].nunique().reset_index()
        cohort_wide  = cohort_pivot.pivot(index="cohort_month", columns="period_number", values="user_id")

        # 归一化为留存率
        cohort_size  = cohort_wide[0]
        retention    = cohort_wide.divide(cohort_size, axis=0)
        retention    = retention.loc[:, retention.columns <= 5]  # 最多展示 6 期

        # 热力图
        ret_labels = [f"M+{c}" if c > 0 else "首月" for c in retention.columns]
        cohort_months_str = [str(m) for m in retention.index]

        fig_cohort = go.Figure(data=go.Heatmap(
            z=retention.values * 100,
            x=ret_labels,
            y=cohort_months_str,
            colorscale="Blues",
            text=[[f"{v:.1f}%" if not np.isnan(v) else "" for v in row]
                  for row in retention.values * 100],
            texttemplate="%{text}",
            textfont=dict(size=11),
            hovertemplate="Cohort: %{y}<br>%{x}: %{z:.1f}%<extra></extra>",
            colorbar=dict(title="留存率（%）")
        ))
        fig_cohort.update_layout(
            title="Cohort 月度留存热力图",
            xaxis_title="距首次支付月份",
            yaxis_title="Cohort 月份",
            height=max(300, len(cohort_months_str) * 50 + 80),
            margin=dict(t=40, b=30, l=100, r=20),
        )
        st.plotly_chart(fig_cohort, use_container_width=True)

        # 留存率趋势对比
        st.markdown("#### 📉 各 Cohort 留存曲线对比")
        fig_ret_line = go.Figure()
        for month_idx, row in retention.iterrows():
            valid = row.dropna()
            if len(valid) > 1:
                fig_ret_line.add_trace(go.Scatter(
                    x=[f"M+{c}" if c > 0 else "首月" for c in valid.index],
                    y=valid.values * 100,
                    mode="lines+markers",
                    name=str(month_idx),
                    line=dict(width=1.5),
                    marker=dict(size=5),
                ))
        fig_ret_line.update_layout(
            title="各 Cohort 留存曲线（%）",
            xaxis_title="距首购月份", yaxis_title="留存率（%）",
            height=340, plot_bgcolor="white",
            legend=dict(title="Cohort月"), margin=dict(t=40, b=30)
        )
        st.plotly_chart(fig_ret_line, use_container_width=True)
    else:
        st.info("当前数据缺少 user_id 字段，无法构建 Cohort 分析。")
else:
    # 展示演示数据
    st.info("使用演示数据展示 Cohort 格式")
    demo_cohort = pd.DataFrame({
        "Cohort": ["2026-01", "2026-02", "2026-03"],
        "首月(M0)": [100, 100, 100],
        "M+1": [48, 51, 50],
        "M+2": [31, 33, None],
        "M+3": [20, None, None],
    }).set_index("Cohort")
    st.dataframe(demo_cohort.style.background_gradient(cmap="Blues", axis=None), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# Section 3: 新老用户对比
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 👥 新客 vs 老客：行为差异对比")

if "is_new_payer" in df.columns and "event_type" in df.columns:
    df_pay2 = df[df["event_type"] == "pay"].copy()
    new_df  = df_pay2[df_pay2["is_new_payer"] == 1]
    old_df  = df_pay2[df_pay2["is_new_payer"] == 0]

    col_new, col_old = st.columns(2)
    for col, label, d, color in [
        (col_new, "🆕 新客", new_df, "#1E5799"),
        (col_old, "🔄 老客", old_df, "#27AE60")
    ]:
        n     = len(d)
        avg_aov = d["order_amount"].mean() if "order_amount" in d.columns else 0
        with col:
            st.markdown(f"""
            <div class="growth-card" style="border-top-color:{color};">
                <div style="font-size:0.8rem;color:#888;">{label}</div>
                <div style="font-size:1.6rem;font-weight:700;color:#1D3557;">{n:,} 次支付</div>
                <div style="font-size:0.85rem;color:#555;">平均客单价：¥{avg_aov:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

    # 日期趋势：新老用户支付数对比
    if "event_time" in df.columns:
        df_pay2["date"] = pd.to_datetime(df_pay2["event_time"]).dt.date
        daily = df_pay2.groupby(["date", "is_new_payer"]).size().reset_index(name="pay_count")
        daily["用户类型"] = daily["is_new_payer"].map({1: "新客", 0: "老客"})

        fig_nu = px.area(
            daily, x="date", y="pay_count", color="用户类型",
            color_discrete_map={"新客": "#1E5799", "老客": "#27AE60"},
            title="新客 vs 老客 每日支付量趋势",
            labels={"pay_count": "支付次数", "date": "日期"},
            height=320
        )
        fig_nu.update_layout(plot_bgcolor="white", margin=dict(t=40, b=30))
        st.plotly_chart(fig_nu, use_container_width=True)
else:
    st.info("数据中未找到 is_new_payer 字段，展示用户类型分布替代。")
    if "user_type" in df.columns:
        utype_df = df[df["event_type"] == "pay"].groupby("user_type").agg(
            pay_count=("event_type", "count"),
            gmv=("order_amount", "sum") if "order_amount" in df.columns else ("event_type", "count")
        ).reset_index()
        fig_ut = px.bar(utype_df, x="user_type", y="pay_count",
                        title="各用户类型支付量", height=320,
                        labels={"pay_count": "支付次数", "user_type": "用户类型"},
                        color="user_type", text_auto=True)
        fig_ut.update_layout(plot_bgcolor="white", showlegend=False)
        st.plotly_chart(fig_ut, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# Section 4: LTV 估算
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 💎 LTV 估算模型")
st.markdown("""<p style="color:#666;font-size:0.88rem;">
LTV（用户生命周期价值）= ARPU × 平均留存周期。调整参数查看不同场景下的 LTV 预测。
</p>""", unsafe_allow_html=True)

col_ltv_input, col_ltv_result = st.columns([1, 1])

with col_ltv_input:
    if gmv_total > 0 and pay_users > 0:
        default_arpu = int(gmv_total / max(pay_users, 1))
    else:
        default_arpu = 150

    arpu    = st.number_input("月均 ARPU（元/月）", min_value=1, value=default_arpu, step=10)
    monthly_retention = st.slider("月留存率（%）", 10, 90, 60, step=5) / 100
    churn_rate = 1 - monthly_retention
    avg_months = 1 / churn_rate if churn_rate > 0 else 24
    ltv = arpu * avg_months
    platform_rate = st.slider("平台佣金率（%）", 1, 20, 5) / 100
    ltv_revenue = ltv * platform_rate

with col_ltv_result:
    st.markdown(f"""
    <div class="growth-card" style="border-top-color:#9B59B6;">
        <div style="font-size:0.8rem;color:#888;margin-bottom:8px;">LTV 计算结果</div>
        <table style="width:100%;font-size:0.85rem;">
            <tr><td style="color:#666;">月均 ARPU</td>
                <td style="text-align:right;font-weight:600;">¥{arpu:,.0f}</td></tr>
            <tr><td style="color:#666;">月留存率</td>
                <td style="text-align:right;font-weight:600;">{monthly_retention:.0%}</td></tr>
            <tr><td style="color:#666;">平均留存月数</td>
                <td style="text-align:right;font-weight:600;">{avg_months:.1f} 个月</td></tr>
            <tr style="background:#EBF5FB;"><td><b>用户 LTV</b></td>
                <td style="text-align:right;font-size:1.3rem;font-weight:700;color:#1E5799;">
                    ¥{ltv:,.0f}</td></tr>
            <tr><td style="color:#666;">平台可获收入 LTV</td>
                <td style="text-align:right;font-weight:600;color:#27AE60;">¥{ltv_revenue:,.0f}</td></tr>
        </table>
        <div style="font-size:0.78rem;color:#888;margin-top:8px;">
            公式：LTV = ARPU × (1 / 月流失率) = {arpu} × {avg_months:.1f} = ¥{ltv:,.0f}
        </div>
    </div>
    """, unsafe_allow_html=True)

# LTV 对比不同留存率
ret_rates = [0.40, 0.50, 0.60, 0.70, 0.80]
ltvs = [arpu / max(1 - r, 0.01) for r in ret_rates]
fig_ltv = go.Figure(go.Bar(
    x=[f"{int(r*100)}%留存" for r in ret_rates],
    y=ltvs,
    marker_color=["#AED6F1" if r != monthly_retention else "#1E5799" for r in ret_rates],
    text=[f"¥{v:,.0f}" for v in ltvs],
    textposition="outside"
))
fig_ltv.update_layout(
    title=f"不同月留存率对应的 LTV（ARPU=¥{arpu}）",
    yaxis_title="LTV（元）", height=300,
    plot_bgcolor="white", margin=dict(t=40, b=30)
)
st.plotly_chart(fig_ltv, use_container_width=True)


# ── SQL 查看器 ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🖥️ 查看背后的 SQL（DuckDB）")

gsql1, gsql2 = st.tabs(["Cohort 留存 SQL", "新老用户对比 SQL"])

with gsql1:
    st.code("""
-- Cohort 月度留存率计算
WITH first_purchase AS (
    -- 每个用户的首次支付月（Cohort 定义）
    SELECT
        user_id,
        DATE_TRUNC('month', MIN(event_time)) AS cohort_month
    FROM distribution_events
    WHERE event_type = 'pay'
    GROUP BY user_id
),
monthly_activity AS (
    -- 每个用户每月的支付活跃情况
    SELECT DISTINCT
        e.user_id,
        f.cohort_month,
        DATE_TRUNC('month', e.event_time) AS activity_month,
        DATEDIFF('month', f.cohort_month, DATE_TRUNC('month', e.event_time)) AS period_number
    FROM distribution_events e
    JOIN first_purchase f ON e.user_id = f.user_id
    WHERE e.event_type = 'pay'
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT user_id) AS total_users
    FROM first_purchase
    GROUP BY cohort_month
),
retention_counts AS (
    SELECT cohort_month, period_number, COUNT(DISTINCT user_id) AS retained_users
    FROM monthly_activity
    GROUP BY cohort_month, period_number
)
SELECT
    r.cohort_month,
    r.period_number,
    r.retained_users,
    c.total_users,
    ROUND(1.0 * r.retained_users / c.total_users, 4) AS retention_rate
FROM retention_counts r
JOIN cohort_size c USING (cohort_month)
ORDER BY r.cohort_month, r.period_number;
""", language="sql")

with gsql2:
    st.code("""
-- 新客 vs 老客行为对比
SELECT
    is_new_payer,
    COUNT(*)                                             AS pay_count,
    COUNT(DISTINCT user_id)                              AS unique_users,
    ROUND(AVG(order_amount), 2)                          AS avg_order_value,
    SUM(order_amount)                                    AS total_gmv,
    ROUND(SUM(order_amount) / COUNT(DISTINCT user_id), 2) AS arpu
FROM distribution_events
WHERE event_type = 'pay'
  AND event_time BETWEEN :start_date AND :end_date
GROUP BY is_new_payer;

-- 新客日均增量趋势
SELECT
    DATE(event_time)                                     AS dt,
    SUM(CASE WHEN is_new_payer = 1 THEN 1 ELSE 0 END)   AS new_payers,
    SUM(CASE WHEN is_new_payer = 0 THEN 1 ELSE 0 END)   AS returning_payers,
    ROUND(1.0 * SUM(CASE WHEN is_new_payer = 1 THEN 1 ELSE 0 END)
               / NULLIF(COUNT(*), 0), 4)                 AS new_payer_rate
FROM distribution_events
WHERE event_type = 'pay'
  AND event_time BETWEEN :start_date AND :end_date
GROUP BY DATE(event_time)
ORDER BY dt;
""", language="sql")

# 侧边栏
st.sidebar.markdown("""
## 📖 增长分析说明

**AARRR 各阶段核心指标**

| 阶段 | 核心指标 |
|------|---------|
| Acquisition | 新增曝光UV、渠道CPA |
| Activation | 首单转化率、激活率 |
| Retention | D1/D7/M1留存率 |
| Revenue | ARPU、LTV、GMV |
| Referral | 新客占比、分享率 |

**LTV 计算公式**
```
LTV = ARPU × (1 / 月流失率)
    = ARPU × (1 / (1 - 月留存率))
```

**Cohort 分析说明**
- 颜色越深 = 留存率越高
- M+1 下降大 = 次月召回是重点
- 不同月份曲线对比可看到产品改进效果
""")
