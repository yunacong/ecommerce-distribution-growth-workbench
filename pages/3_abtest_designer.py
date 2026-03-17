"""
3_abtest_designer.py — A/B Test 设计助手页（v2.0）

新增功能：
  - 样本量计算器（基准率 + 期望提升 + 置信度 → 所需样本量 & 实验天数）
  - SRM 检测（Sample Ratio Mismatch, χ² 检验）
  - 统计显著性检验（z-test, p-value, 置信区间展示）
"""
import streamlit as st
import sys, os
import math
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.abtest_generator import generate_abtest_plan, _strategy_label
from modules.data_loader import load_data, get_filter_options

st.set_page_config(page_title="A/B Test 设计助手", page_icon="🧪", layout="wide")

st.markdown("""
<style>
.plan-section { background:white; border-radius:10px; padding:1.2rem 1.4rem; margin-bottom:0.8rem;
                box-shadow:0 1px 6px rgba(0,0,0,0.07); border:1px solid #EBF5FB; }
.plan-section h4 { margin-bottom:0.5rem; color:#1D3557; }
.tag { display:inline-block; background:#EBF5FB; color:#1E5799; border-radius:4px;
       padding:2px 10px; font-size:0.82rem; margin:2px 3px; border:1px solid #AED6F1; }
.tag.primary { background:#1E5799; color:white; border-color:#1E5799; }
.tag.secondary { background:#2E86AB; color:white; border-color:#2E86AB; }
.tag.guardrail { background:#FEF9E7; color:#F39C12; border-color:#F9E79F; }
.risk-item { background:#FDEDEC; border-radius:6px; padding:6px 10px; margin:4px 0;
             border-left:3px solid #E74C3C; font-size:0.85rem; }
.success-item { background:#EAFAF1; border-radius:6px; padding:6px 10px; margin:4px 0;
                border-left:3px solid #27AE60; font-size:0.85rem; }
.stat-card { background:white; border-radius:10px; padding:1.2rem 1.4rem; margin-bottom:0.8rem;
             box-shadow:0 2px 8px rgba(0,0,0,0.08); }
.sig-pass { background:#EAFAF1; border:1px solid #A9DFBF; border-radius:8px; padding:1rem;
            border-left:4px solid #27AE60; }
.sig-fail { background:#FDEDEC; border:1px solid #F5B7B1; border-radius:8px; padding:1rem;
            border-left:4px solid #E74C3C; }
.srm-warn { background:#FEF9E7; border:1px solid #F9E79F; border-radius:8px; padding:1rem;
            border-left:4px solid #F39C12; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
## 🧪 A/B Test 设计助手
<p style="color:#666;font-size:0.93rem;">
本页面将策略机会点转化为结构化实验方案，并内置统计显著性工具箱：样本量计算器、SRM 检测、p-value 显著性检验，
确保每个实验有统计学支撑。
</p>
<hr style="border-color:#E8EDF0;margin-bottom:1.2rem">
""", unsafe_allow_html=True)

# ── Tab 布局 ──────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 实验方案生成", "📐 样本量计算器", "📊 显著性检验 & SRM"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: 实验方案生成（原有功能）
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    df_full = load_data()
    opts = get_filter_options(df_full)

    st.markdown("### 📝 实验信息输入")
    col_form, col_preview = st.columns([2, 3])

    with col_form:
        with st.form("abtest_form"):
            st.markdown("#### 🏷️ 基础信息")
            strategy_name = st.text_input(
                "实验/策略名称 *",
                value="recommendation_feed 展示优化实验",
                placeholder="例：新客展示优化实验"
            )
            business_goal = st.selectbox(
                "业务目标 *",
                ["提升CTR", "提升CVR", "提升GMV", "提升新客支付率", "提升召回点击率", "提升ROI"]
            )
            problem_type = st.selectbox(
                "当前问题类型 *",
                options=[
                    ("low_ctr",          "高曝光低点击（CTR 偏低）"),
                    ("low_conversion",   "高点击低转化（CVR 偏低）"),
                    ("low_roi",          "ROI 低/成本高"),
                    ("group_difference", "分群差异明显"),
                    ("reactivation_need","用户沉默/召回需求"),
                ],
                format_func=lambda x: x[1],
            )

            st.markdown("#### 🛠️ 策略信息")
            strategy_type = st.selectbox(
                "策略类型 *",
                options=[
                    ("display_optimization",  "展示优化（封面/标题/样式）"),
                    ("ranking_adjustment",    "排序与分发优化"),
                    ("detail_optimization",   "详情页承接优化"),
                    ("coupon",                "优惠券发放"),
                    ("subsidy",               "补贴激励"),
                    ("reactivation_push",     "召回触达"),
                ],
                format_func=lambda x: x[1],
            )
            hypothesis = st.text_area(
                "实验假设 * (100字以内)",
                value="对 recommendation_feed 中的 short_video 展示形式进行优化，预计可提升 new_user 的 CTR 约 8-12%。",
                max_chars=200,
                height=80,
            )

            st.markdown("#### 🎯 目标范围")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                target_channel = st.selectbox("目标场景", opts["channel"] + ["all"])
                target_user    = st.selectbox("目标人群", opts["user_type"] + ["all_users"])
            with col_r2:
                target_content = st.selectbox("目标内容类型", opts["content_type"] + ["all"])
                target_cat     = st.selectbox("目标商品类目", opts["item_category"] + ["all"])
            target_price = st.selectbox("目标价格带", opts["price_band"] + ["all"])

            st.markdown("#### ⚙️ 实验偏好")
            duration_pref = st.select_slider(
                "观察周期偏好",
                options=["auto（系统推荐）", "7天", "14天", "21天"],
                value="auto（系统推荐）"
            )
            cost_flag = st.checkbox("⚠️ 成本敏感（ROI / Campaign Cost 为重要护栏）", value=False)
            risk_note = st.text_area("已知风险备注（可选）", height=60,
                                     placeholder="例：当前实验期间有大促，可能影响基线...")
            submit = st.form_submit_button("🚀 生成实验方案", type="primary", use_container_width=True)

    if submit or "abtest_plan" in st.session_state:
        if submit:
            duration_map = {
                "auto（系统推荐）": "auto",
                "7天": "7_days", "14天": "14_days", "21天": "21_days"
            }
            input_params = {
                "strategy_name":                 strategy_name,
                "business_goal":                 business_goal,
                "problem_type":                  problem_type[0],
                "strategy_type":                 strategy_type[0],
                "hypothesis":                    hypothesis,
                "target_channel":                target_channel,
                "target_user_group":             target_user,
                "target_content_type":           target_content,
                "target_item_category":          target_cat,
                "target_price_band":             target_price,
                "experiment_duration_preference":duration_map.get(duration_pref, "auto"),
                "cost_sensitive_flag":           cost_flag,
                "risk_note":                     risk_note,
            }
            result = generate_abtest_plan(input_params)
            st.session_state["abtest_plan"] = result

        plan_data = st.session_state.get("abtest_plan", {})
        if not plan_data:
            st.info("请填写表单后点击「生成实验方案」")
            st.stop()

        plan = plan_data["plan"]
        markdown_text = plan_data["markdown"]

        with col_preview:
            st.markdown("### 📋 生成的实验方案")

            st.markdown(f"""
            <div class="plan-section">
                <h4>🏷️ {plan["strategy_name"]}</h4>
                <div style="font-size:0.85rem;color:#555;margin-bottom:0.5rem;">{plan["problem_background"]}</div>
                <div><strong>业务目标：</strong>{plan["business_goal"]}</div>
                <div style="margin-top:6px;font-style:italic;color:#444;font-size:0.88rem;">
                    💬 假设：{plan["hypothesis"]}
                </div>
            </div>
            """, unsafe_allow_html=True)

            t = plan["target"]
            st.markdown(f"""
            <div class="plan-section">
                <h4>🎯 实验对象</h4>
                <span class="tag">场景：{t["channel"]}</span>
                <span class="tag">人群：{t["user_group"]}</span>
                <span class="tag">内容：{t["content_type"]}</span>
                <span class="tag">类目：{t["item_category"]}</span>
                <span class="tag">价格带：{t["price_band"]}</span>
            </div>
            """, unsafe_allow_html=True)

            groups_html = "".join([
                f'<div style="background:#F8F9FA;border-radius:6px;padding:6px 10px;margin-bottom:6px;">'
                f'<strong style="color:#1E5799;">{g}</strong>: {desc}'
                f'</div>'
                for g, desc in plan["groups"].items()
            ])
            st.markdown(f"""
            <div class="plan-section">
                <h4>👥 分组方式</h4>
                {groups_html}
            </div>
            """, unsafe_allow_html=True)

            primary_tags   = "".join([f'<span class="tag primary">{m}</span>' for m in plan["primary_metrics"]])
            secondary_tags = "".join([f'<span class="tag secondary">{m}</span>' for m in plan["secondary_metrics"]])
            guardrail_tags = "".join([f'<span class="tag guardrail">{m}</span>' for m in plan["guardrail_metrics"]])

            st.markdown(f"""
            <div class="plan-section">
                <h4>📊 指标体系</h4>
                <div style="margin-bottom:6px;"><strong>主指标：</strong> {primary_tags}</div>
                <div style="margin-bottom:6px;"><strong>辅助指标：</strong> {secondary_tags}</div>
                <div><strong>护栏指标：</strong> {guardrail_tags}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="plan-section">
                <h4>⏱️ 观察周期 & 成功判定</h4>
                <div style="margin-bottom:0.4rem;">
                    <strong>建议周期：</strong>{plan["duration"]}
                    <span style="font-size:0.82rem;color:#888;"> — {plan["duration_reason"]}</span>
                </div>
                <div class="success-item">
                    ✅ <strong>成功判定标准：</strong>{plan["success_criteria"]}
                </div>
            </div>
            """, unsafe_allow_html=True)

            risks_html = "".join([f'<div class="risk-item">⚠️ {r}</div>' for r in plan["risks"]])
            st.markdown(f"""
            <div class="plan-section">
                <h4>⚠️ 风险提示</h4>
                {risks_html}
            </div>
            """, unsafe_allow_html=True)

            review_html = "".join([
                f'<div style="background:#EBF5FB;border-radius:4px;padding:5px 10px;margin:3px 0;font-size:0.85rem;">'
                f'🔍 {r}</div>'
                for r in plan["review_focus"]
            ])
            st.markdown(f"""
            <div class="plan-section">
                <h4>📝 复盘重点</h4>
                {review_html}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📄 Markdown 方案草稿（可直接复制到 Notion）")
        col_md, col_btn = st.columns([4, 1])
        with col_md:
            st.code(markdown_text, language="markdown")
        with col_btn:
            st.download_button(
                label="⬇️ 下载方案",
                data=markdown_text.encode("utf-8"),
                file_name=f"{plan['strategy_name']}_实验方案.md",
                mime="text/markdown",
                use_container_width=True,
            )
            st.page_link("pages/4_ai_review.py", label="🤖 AI 复盘页", icon="🤖")

    else:
        with col_preview:
            st.markdown("### 📋 实验方案预览")
            st.markdown("""
            <div style="background:#F5F7FA;border-radius:10px;padding:2rem;text-align:center;color:#888;height:400px;
                        display:flex;align-items:center;justify-content:center;flex-direction:column;">
                <div style="font-size:2.5rem;margin-bottom:1rem;">🧪</div>
                <div style="font-size:1rem;font-weight:600;margin-bottom:0.5rem;">填写左侧表单后生成实验方案</div>
                <div style="font-size:0.85rem;">系统将自动推荐指标体系、分组方式、观察周期和风险提示</div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: 样本量计算器
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📐 样本量计算器")
    st.markdown("""
    <p style="color:#666;font-size:0.9rem;">
    根据基准转化率、期望提升幅度、置信水平和检验效能，计算最小样本量和建议实验天数。
    公式来源：<code>n = (Z_α + Z_β)² × 2p(1-p) / δ²</code>
    </p>
    """, unsafe_allow_html=True)

    col_input, col_result = st.columns([1, 1])

    with col_input:
        st.markdown("#### ⚙️ 输入参数")

        baseline_rate = st.number_input(
            "基准转化率（%）",
            min_value=0.1, max_value=99.0, value=6.4, step=0.1,
            help="当前控制组的转化率，如 CTR=6.4%"
        )
        expected_lift = st.number_input(
            "期望最小可检测提升（%）",
            min_value=0.5, max_value=50.0, value=10.0, step=0.5,
            help="相对提升幅度，如 CTR 从 6.4% 提升到 7.04%，相对提升=10%"
        )
        confidence = st.select_slider(
            "置信水平（1-α）",
            options=[0.90, 0.95, 0.99],
            value=0.95,
            format_func=lambda x: f"{int(x*100)}%"
        )
        power = st.select_slider(
            "检验效能（1-β）",
            options=[0.70, 0.80, 0.90],
            value=0.80,
            format_func=lambda x: f"{int(x*100)}%"
        )
        daily_traffic = st.number_input(
            "每日可用流量（人/天）",
            min_value=100, max_value=10_000_000, value=100_000, step=1000,
            help="实验期间控制组+实验组的总日流量"
        )
        traffic_ratio = st.slider(
            "实验组流量占比",
            min_value=0.1, max_value=0.9, value=0.5, step=0.05,
            format="%.0f%%",
            help="实验组占总流量的比例，剩余为控制组"
        )

        calc_btn = st.button("🔢 计算样本量", type="primary", use_container_width=True)

    with col_result:
        st.markdown("#### 📊 计算结果")

        if calc_btn or "sample_result" in st.session_state:
            if calc_btn:
                # 统计计算
                alpha = 1 - confidence
                p = baseline_rate / 100
                mde = p * (expected_lift / 100)   # 绝对差值
                p2 = p + mde                       # 实验组期望率

                z_alpha = stats.norm.ppf(1 - alpha / 2)   # 双尾
                z_beta  = stats.norm.ppf(power)

                # 最小样本量公式（每组）
                n_per_group = math.ceil(
                    (z_alpha + z_beta) ** 2 * (p * (1 - p) + p2 * (1 - p2)) / (mde ** 2)
                )
                n_total = n_per_group * 2

                # 实验天数估算
                exp_daily = int(daily_traffic * traffic_ratio)
                ctrl_daily = daily_traffic - exp_daily
                min_daily = min(exp_daily, ctrl_daily)
                days_needed = math.ceil(n_per_group / min_daily)

                st.session_state["sample_result"] = {
                    "n_per_group": n_per_group,
                    "n_total": n_total,
                    "days_needed": days_needed,
                    "p": p, "p2": p2, "mde": mde,
                    "z_alpha": z_alpha, "z_beta": z_beta,
                    "baseline_rate": baseline_rate,
                    "expected_lift": expected_lift,
                }

            res = st.session_state["sample_result"]

            # 结果卡片
            r1, r2, r3 = st.columns(3)
            r1.metric("每组最小样本量", f"{res['n_per_group']:,}")
            r2.metric("总样本量（两组）", f"{res['n_total']:,}")
            r3.metric("建议实验天数", f"{res['days_needed']} 天")

            st.markdown("---")
            st.markdown("#### 📐 计算过程透明化")
            st.markdown(f"""
| 参数 | 数值 | 说明 |
|------|------|------|
| 基准转化率 p | {res['baseline_rate']}% | 控制组当前水平 |
| 期望转化率 p₂ | {res['p2']*100:.2f}% | 基准 × (1 + {res['expected_lift']}%) |
| MDE（绝对差） | {res['mde']*100:.3f}pp | p₂ - p |
| Z_α（双尾） | {res['z_alpha']:.4f} | 置信水平对应 Z 值 |
| Z_β | {res['z_beta']:.4f} | 检验效能对应 Z 值 |
| **每组最小样本** | **{res['n_per_group']:,}** | **(Z_α+Z_β)²·2p(1-p)/δ²** |
""")

            # 可视化：不同 MDE 下的样本量曲线
            lifts = np.arange(5, 31, 1)
            sample_sizes = []
            for lift in lifts:
                _mde = res['p'] * (lift / 100)
                _p2  = res['p'] + _mde
                _n   = math.ceil(
                    (res['z_alpha'] + res['z_beta']) ** 2
                    * (res['p'] * (1 - res['p']) + _p2 * (1 - _p2))
                    / (_mde ** 2)
                )
                sample_sizes.append(_n)

            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=lifts, y=sample_sizes,
                mode="lines+markers",
                line=dict(color="#1E5799", width=2),
                marker=dict(size=5),
                name="每组样本量"
            ))
            fig.add_vline(
                x=res['expected_lift'],
                line_dash="dash", line_color="#E74C3C",
                annotation_text=f"当前设定 {res['expected_lift']}%",
                annotation_position="top right"
            )
            fig.update_layout(
                title="不同期望提升幅度下的所需样本量",
                xaxis_title="期望相对提升幅度（%）",
                yaxis_title="每组最小样本量",
                height=300,
                margin=dict(t=40, b=30, l=50, r=20),
                plot_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.markdown("""
            <div style="background:#F5F7FA;border-radius:10px;padding:2rem;text-align:center;color:#888;
                        display:flex;align-items:center;justify-content:center;flex-direction:column;height:300px;">
                <div style="font-size:2rem;margin-bottom:1rem;">📐</div>
                <div>填写左侧参数后点击「计算样本量」</div>
            </div>
            """, unsafe_allow_html=True)

    # 公式说明
    with st.expander("📖 统计学原理说明"):
        st.markdown("""
**样本量计算公式（双样本比例检验）**

$$n = \\frac{(Z_{\\alpha/2} + Z_{\\beta})^2 \\cdot [p_1(1-p_1) + p_2(1-p_2)]}{\\delta^2}$$

| 符号 | 含义 | 常用取值 |
|------|------|---------|
| Z_α/2 | 置信水平对应的 Z 值（双尾） | 95% → 1.96 |
| Z_β | 检验效能对应的 Z 值 | 80% → 0.84 |
| p₁ | 控制组转化率（基准） | 实测值 |
| p₂ | 实验组期望转化率 | p₁ × (1 + lift%) |
| δ | 最小可检测差值 MDE | p₂ - p₁ |

**关键原则**
- MDE 越小，所需样本量越大（4倍关系：MDE 减半 → 样本量 ×4）
- 置信水平越高 (99% vs 95%)，所需样本量越大
- 实验前必须固定样本量，不能边看数据边决定停止（防止 Peeking 问题）
        """)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: 显著性检验 & SRM 检测
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📊 实验结果显著性检验 & SRM 检测")
    st.markdown("""
    <p style="color:#666;font-size:0.9rem;">
    实验结束后，输入实际观测数据，系统自动完成：① SRM（样本比例不均衡）检测 ② 统计显著性 z-test ③ 置信区间计算
    </p>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.markdown("#### 📥 输入实验数据")

        exp_design_ratio = st.number_input(
            "设计实验组流量占比（%）",
            min_value=10, max_value=90, value=50,
            help="实验方案设计时的分配比例"
        )

        st.markdown("**控制组（Control）**")
        ctrl_users = st.number_input("控制组 · 曝光用户数", min_value=1, value=48500, step=100)
        ctrl_conv  = st.number_input("控制组 · 转化用户数", min_value=0, value=3008, step=10)

        st.markdown("**实验组（Treatment）**")
        treat_users = st.number_input("实验组 · 曝光用户数", min_value=1, value=51500, step=100)
        treat_conv  = st.number_input("实验组 · 转化用户数", min_value=0, value=3685, step=10)

        alpha_test = st.select_slider(
            "显著性水平 α",
            options=[0.01, 0.05, 0.10],
            value=0.05,
            format_func=lambda x: f"{x} （置信度 {int((1-x)*100)}%）"
        )

        test_btn = st.button("🔬 开始检验", type="primary", use_container_width=True)

    with col_b:
        st.markdown("#### 📊 检验结果")

        if test_btn:
            total_users = ctrl_users + treat_users
            actual_treat_ratio = treat_users / total_users
            designed_treat_ratio = exp_design_ratio / 100

            # ── SRM 检测（χ² 检验）──────────────────────────────────────
            expected_ctrl  = total_users * (1 - designed_treat_ratio)
            expected_treat = total_users * designed_treat_ratio
            chi2_stat = ((ctrl_users - expected_ctrl) ** 2 / expected_ctrl +
                         (treat_users - expected_treat) ** 2 / expected_treat)
            srm_p = 1 - stats.chi2.cdf(chi2_stat, df=1)
            srm_detected = srm_p < 0.05

            if srm_detected:
                st.markdown(f"""
                <div class="srm-warn">
                    <strong>⚠️ 检测到 SRM（样本比例不均衡）</strong><br>
                    设计实验组比例：{designed_treat_ratio:.1%}，实际：{actual_treat_ratio:.1%}<br>
                    χ² = {chi2_stat:.3f}，SRM p-value = {srm_p:.4f}<br>
                    <small>结论：流量分配存在系统性偏差，建议 <strong>暂停分析，排查原因</strong>（Bot流量/缓存/分层错误）后重做实验</small>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="sig-pass">
                    ✅ <strong>SRM 检测通过</strong><br>
                    设计比例：{designed_treat_ratio:.1%}，实际：{actual_treat_ratio:.1%}<br>
                    χ² = {chi2_stat:.3f}，SRM p-value = {srm_p:.4f} ≥ 0.05，分配均衡。
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")

            # ── 统计显著性检验（双比例 z-test）────────────────────────────
            ctrl_rate  = ctrl_conv / ctrl_users
            treat_rate = treat_conv / treat_users
            lift_abs   = treat_rate - ctrl_rate
            lift_rel   = lift_abs / ctrl_rate if ctrl_rate > 0 else 0

            # z-test
            p_pool = (ctrl_conv + treat_conv) / (ctrl_users + treat_users)
            se = math.sqrt(p_pool * (1 - p_pool) * (1/ctrl_users + 1/treat_users))
            z_stat = lift_abs / se if se > 0 else 0
            p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))   # 双尾
            is_sig = p_value < alpha_test

            # 置信区间
            z_ci = stats.norm.ppf(1 - alpha_test / 2)
            se_ci = math.sqrt(ctrl_rate*(1-ctrl_rate)/ctrl_users + treat_rate*(1-treat_rate)/treat_users)
            ci_low  = lift_abs - z_ci * se_ci
            ci_high = lift_abs + z_ci * se_ci

            css_class = "sig-pass" if is_sig else "sig-fail"
            verdict   = "✅ 实验组显著优于控制组，建议上线" if is_sig else "❌ 差异不显著，建议延长观察或放弃"

            st.markdown(f"""
            <div class="{css_class}">
                <strong>{verdict}</strong><br>
                控制组转化率：{ctrl_rate:.2%} &nbsp;|&nbsp; 实验组转化率：{treat_rate:.2%}<br>
                绝对提升：{lift_abs*100:+.3f}pp &nbsp;|&nbsp; 相对提升：{lift_rel*100:+.1f}%<br>
                z = {z_stat:.3f}，<strong>p-value = {p_value:.4f}</strong>，α = {alpha_test}<br>
                {int((1-alpha_test)*100)}% 置信区间：[{ci_low*100:+.3f}pp, {ci_high*100:+.3f}pp]
            </div>
            """, unsafe_allow_html=True)

            # 可视化：正态分布 + 临界值
            x = np.linspace(-4, 4, 400)
            y = stats.norm.pdf(x)
            z_crit = stats.norm.ppf(1 - alpha_test / 2)

            fig2 = go.Figure()
            # 拒绝域（左）
            x_left = x[x <= -z_crit]
            fig2.add_trace(go.Scatter(x=x_left, y=stats.norm.pdf(x_left),
                fill="tozeroy", fillcolor="rgba(231,76,60,0.25)", line=dict(width=0), name="拒绝域"))
            # 拒绝域（右）
            x_right = x[x >= z_crit]
            fig2.add_trace(go.Scatter(x=x_right, y=stats.norm.pdf(x_right),
                fill="tozeroy", fillcolor="rgba(231,76,60,0.25)", line=dict(width=0), showlegend=False))
            # 分布曲线
            fig2.add_trace(go.Scatter(x=x, y=y, mode="lines",
                line=dict(color="#1E5799", width=2), name="标准正态分布"))
            # 统计量 z
            fig2.add_vline(x=z_stat, line_dash="solid", line_color="#E74C3C" if is_sig else "#F39C12",
                           annotation_text=f"z={z_stat:.2f}", annotation_position="top right")
            fig2.add_vline(x=-z_crit, line_dash="dash", line_color="#888",
                           annotation_text=f"±{z_crit:.2f}", annotation_position="top left")
            fig2.add_vline(x=z_crit, line_dash="dash", line_color="#888")

            fig2.update_layout(
                title=f"显著性检验（p={p_value:.4f}，α={alpha_test}）",
                xaxis_title="z 统计量", yaxis_title="概率密度",
                height=280, margin=dict(t=40, b=30, l=40, r=20),
                plot_bgcolor="white", showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)

            # 汇总表
            st.markdown("**📋 完整检验摘要**")
            summary = {
                "项目": ["控制组用户数", "实验组用户数", "控制组转化率", "实验组转化率",
                         "绝对提升", "相对提升", "z 统计量", "p-value", "是否显著"],
                "数值": [f"{ctrl_users:,}", f"{treat_users:,}", f"{ctrl_rate:.4%}", f"{treat_rate:.4%}",
                         f"{lift_abs*100:+.3f}pp", f"{lift_rel*100:+.2f}%",
                         f"{z_stat:.4f}", f"{p_value:.4f}", "✅ 是" if is_sig else "❌ 否"]
            }
            import pandas as pd
            st.dataframe(pd.DataFrame(summary), hide_index=True, use_container_width=True)

        else:
            st.markdown("""
            <div style="background:#F5F7FA;border-radius:10px;padding:2rem;text-align:center;color:#888;
                        display:flex;align-items:center;justify-content:center;flex-direction:column;height:350px;">
                <div style="font-size:2rem;margin-bottom:1rem;">🔬</div>
                <div>输入实验数据后点击「开始检验」</div>
                <div style="font-size:0.8rem;margin-top:0.5rem;">将自动完成 SRM 检测 + 显著性 z-test</div>
            </div>
            """, unsafe_allow_html=True)

# 侧边栏
st.sidebar.markdown("""
## 📖 使用指南

**Tab 1 · 方案生成**
填写实验信息 → 自动生成主/辅/护栏指标、分组、周期

**Tab 2 · 样本量计算**
实验设计阶段必做，防止实验力不足或过度设计

**Tab 3 · 显著性检验**
实验结束后输入数据，完成 SRM + p-value 全套检验

---
**统计学标准**

| 参数 | 推荐值 |
|------|--------|
| 置信水平 | 95% |
| 检验效能 | 80% |
| 显著性 α | 0.05 |
| 最小实验周期 | ≥7天（避免新奇效应）|
""")
