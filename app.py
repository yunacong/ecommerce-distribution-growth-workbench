"""
app.py — 抖音电商平台分发增长与策略优化工作台
Streamlit 入口文件
"""
import streamlit as st

st.set_page_config(
    page_title="电商平台策略优化工作台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全局样式 ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 主色调 */
:root {
    --primary: #1E5799;
    --accent:  #2E86AB;
    --danger:  #E74C3C;
    --success: #27AE60;
    --bg:      #F5F7FA;
}

/* 侧边栏 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1D3557 0%, #1E5799 100%);
}
[data-testid="stSidebar"] * {
    color: #ECF0F1 !important;
}
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stDateInput label,
[data-testid="stSidebar"] .stSelectbox label {
    color: #BDC3C7 !important;
    font-size: 0.85rem !important;
}

/* 指标卡片 */
.metric-card {
    background: white;
    border-radius: 12px;
    padding: 1.2rem 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-left: 4px solid #1E5799;
    transition: box-shadow 0.2s;
}
.metric-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.12); }
.metric-card.danger { border-left-color: #E74C3C; }
.metric-card.success { border-left-color: #27AE60; }
.metric-card.warning { border-left-color: #F39C12; }

/* 诊断摘要框 */
.diagnosis-box {
    background: #EBF5FB;
    border: 1px solid #AED6F1;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
}
.diagnosis-box.warning {
    background: #FEF9E7;
    border-color: #F9E79F;
}
.diagnosis-box.danger {
    background: #FDEDEC;
    border-color: #F5B7B1;
}
.diagnosis-box.success {
    background: #EAFAF1;
    border-color: #A9DFBF;
}

/* 页面标题 */
.page-header {
    padding: 0.5rem 0 1rem 0;
    border-bottom: 2px solid #1E5799;
    margin-bottom: 1.5rem;
}
.page-subtitle {
    color: #666;
    font-size: 0.92rem;
    margin-top: 0.3rem;
}

/* Tab 样式 */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px 6px 0 0;
    padding: 0.5rem 1.2rem;
}

/* 实验方案卡片 */
.plan-card {
    background: white;
    border-radius: 10px;
    padding: 1.2rem;
    margin: 0.5rem 0;
    box-shadow: 0 1px 6px rgba(0,0,0,0.08);
    border: 1px solid #EBF5FB;
}
</style>
""", unsafe_allow_html=True)

# ── 首页内容 ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h1>📊 抖音电商平台分发增长与策略优化工作台</h1>
    <p class="page-subtitle">Distribution Growth & Strategy Optimization Workbench · 面向平台业务团队的一体化策略分析工具</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("""
    ### 🎯 项目简介

    本工作台围绕抖音电商推荐场景中的 **CTR、CVR、GMV** 三大核心指标，
    为策略产品经理、增长运营、数据分析师提供从**问题发现 → 漏斗归因 → 实验设计 → AI 复盘**的完整分析闭环。

    ---

    ### 🗺️ 核心业务流程
    """)

    steps_html = """
    <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin: 0.5rem 0 1rem 0;">
        <div style="background:#1E5799;color:white;padding:8px 16px;border-radius:6px;font-size:0.9rem;">
            📊 Dashboard<br><small>发现异常</small>
        </div>
        <div style="color:#1E5799;font-size:1.5rem;">→</div>
        <div style="background:#2E86AB;color:white;padding:8px 16px;border-radius:6px;font-size:0.9rem;">
            🔍 漏斗分析<br><small>定位问题</small>
        </div>
        <div style="color:#1E5799;font-size:1.5rem;">→</div>
        <div style="background:#457B9D;color:white;padding:8px 16px;border-radius:6px;font-size:0.9rem;">
            🧪 A/B 实验<br><small>验证策略</small>
        </div>
        <div style="color:#1E5799;font-size:1.5rem;">→</div>
        <div style="background:#1D3557;color:white;padding:8px 16px;border-radius:6px;font-size:0.9rem;">
            🤖 AI 复盘<br><small>沉淀结论</small>
        </div>
    </div>
    """
    st.markdown(steps_html, unsafe_allow_html=True)

    st.markdown("""
    ### 📋 核心页面说明

    | 页面 | 职责 | 核心输出 |
    |------|------|----------|
    | 📊 策略总览 Dashboard | 指标监控 & 异常识别 | CTR/CVR/GMV 看板、趋势图、异常提示 |
    | 🔍 漏斗分析与归因 | 链路拆解 & 问题定位 | 漏斗图、分群对比、问题摘要 |
    | 🧪 A/B Test 设计助手 | 策略方案自动生成 | 实验指标、分组方案、Markdown 文案 |
    | 🤖 AI 复盘与策略建议 | 结构化复盘 & 放量建议 | 异常诊断、实验复盘、后续动作 |
    """)

with col2:
    st.markdown("""
    ### 📈 本次数据集概览
    """)

    try:
        from modules.data_loader import load_data
        df = load_data()

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("📅 数据周期", f"{df['event_date'].min().strftime('%m/%d')} ~ {df['event_date'].max().strftime('%m/%d')}")
            st.metric("📦 数据行数", f"{len(df):,} 行")
        with col_b:
            st.metric("📡 流量场景数", f"{df['channel'].nunique()} 个")
            st.metric("🧪 实验组", f"{df['experiment_group'].nunique()} 组")

        from modules.metric_calculator import calc_core_metrics
        m = calc_core_metrics(df)

        st.markdown("**全量数据核心指标基线**")
        c1, c2, c3 = st.columns(3)
        c1.metric("CTR", f"{m['ctr']*100:.2f}%")
        c2.metric("CVR", f"{m['cvr']*100:.2f}%")
        c3.metric("GMV", f"¥{m['gmv']/10000:.0f}万")

    except Exception as e:
        st.warning(f"数据加载中... {e}")

    st.markdown("""
    ---
    ### 🚀 快速开始

    👈 使用左侧导航菜单进入各功能页面

    **推荐路径：**
    1. 先看 **Dashboard** 识别当前指标异常
    2. 进入 **漏斗分析** 定位问题环节
    3. 用 **A/B Test 助手** 设计实验方案
    4. 在 **AI 复盘** 页生成结构化结论

    ---
    ### ⚙️ 技术栈
    `Python` · `Streamlit` · `Plotly` · `Pandas` · `Claude API`
    """)

# 侧边栏导航提示
st.sidebar.markdown("""
<div style="text-align:center; padding: 1rem 0;">
    <h3 style="color:white; font-size:1.1rem;">🗂️ 功能导航</h3>
</div>
""", unsafe_allow_html=True)
st.sidebar.page_link("pages/1_dashboard.py",         label="📊 策略总览 Dashboard")
st.sidebar.page_link("pages/2_funnel_analysis.py",   label="🔍 漏斗分析与归因")
st.sidebar.page_link("pages/3_abtest_designer.py",   label="🧪 A/B Test 设计助手")
st.sidebar.page_link("pages/4_ai_review.py",         label="🤖 AI 复盘与策略建议")
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align:center; font-size:0.75rem; color:#BDC3C7; padding:0.5rem;">
抖音电商平台<br>分发增长与策略优化工作台<br>v1.0 · Demo
</div>
""", unsafe_allow_html=True)
