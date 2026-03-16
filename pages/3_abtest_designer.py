"""
3_abtest_designer.py — A/B Test 设计助手页

解决问题：将漏斗分析阶段识别出的策略机会点转化为标准化实验方案，
          降低实验设计门槛，提升跨团队协作效率。
"""
import streamlit as st
import sys, os
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
</style>
""", unsafe_allow_html=True)

st.markdown("""
## 🧪 A/B Test 设计助手页
<p style="color:#666;font-size:0.93rem;">
本页面将策略机会点转化为结构化实验方案。输入业务目标与策略信息后，
系统自动推荐主指标、辅助指标、护栏指标、分组方式、观察周期和风险提示，
并生成可直接复制到 Notion 的 Markdown 文案。
</p>
<hr style="border-color:#E8EDF0;margin-bottom:1.2rem">
""", unsafe_allow_html=True)

# ── 数据选项 ──────────────────────────────────────────────────────────────────
df_full = load_data()
opts = get_filter_options(df_full)

# ── 输入表单 ──────────────────────────────────────────────────────────────────
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
            value=f"对 recommendation_feed 中的 short_video 展示形式进行优化，预计可提升 new_user 的 CTR 约 8-12%。",
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
        risk_note = st.text_area("已知风险备注（可选）", height=60, placeholder="例：当前实验期间有大促，可能影响基线...")

        submit = st.form_submit_button("🚀 生成实验方案", type="primary", use_container_width=True)

# ── 生成逻辑 ──────────────────────────────────────────────────────────────────
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

        # ── 实验名称与目标 ──
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

        # ── 实验对象 ──
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

        # ── 分组方式 ──
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

        # ── 指标体系 ──
        primary_tags    = "".join([f'<span class="tag primary">{m}</span>' for m in plan["primary_metrics"]])
        secondary_tags  = "".join([f'<span class="tag secondary">{m}</span>' for m in plan["secondary_metrics"]])
        guardrail_tags  = "".join([f'<span class="tag guardrail">{m}</span>' for m in plan["guardrail_metrics"]])

        st.markdown(f"""
        <div class="plan-section">
            <h4>📊 指标体系</h4>
            <div style="margin-bottom:6px;"><strong>主指标：</strong> {primary_tags}</div>
            <div style="margin-bottom:6px;"><strong>辅助指标：</strong> {secondary_tags}</div>
            <div><strong>护栏指标：</strong> {guardrail_tags}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── 周期 & 成功判定 ──
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

        # ── 风险提示 ──
        risks_html = "".join([f'<div class="risk-item">⚠️ {r}</div>' for r in plan["risks"]])
        st.markdown(f"""
        <div class="plan-section">
            <h4>⚠️ 风险提示</h4>
            {risks_html}
        </div>
        """, unsafe_allow_html=True)

        # ── 复盘重点 ──
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

    # ── Markdown 导出 ─────────────────────────────────────────────────────────
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

# 侧边栏说明
st.sidebar.markdown("""
## 📖 使用说明

1. **填写基础信息**：策略名称、业务目标、问题类型
2. **选择策略类型**：决定指标推荐和分组逻辑
3. **填写实验假设**：描述预期效果
4. **设定目标范围**：场景/人群/内容/类目
5. **点击生成方案**：查看结构化实验草案
6. **复制 Markdown**：直接粘贴到 Notion

---
**指标推荐规则**

| 业务目标 | 主指标 |
|---------|--------|
| 提升CTR | CTR |
| 提升CVR | CVR |
| 提升GMV | GMV |
| 新客效果 | New User Rate |
| 提升ROI | ROI |
""")
