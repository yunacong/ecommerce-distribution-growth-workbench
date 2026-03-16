# 📊 抖音电商平台分发增长与策略优化工作台

> **Distribution Growth & Strategy Optimization Workbench**
> 面向平台业务团队的一体化策略分析 Demo — 问题发现 · 漏斗归因 · 实验设计 · AI 复盘

---

## 🎯 项目简介

本项目围绕抖音电商推荐场景中的 **CTR、CVR、GMV** 三大核心指标，模拟平台侧策略产品/增长策略产品的真实工作方式，构建一套面向业务团队（策略 PM、增长运营、数据分析师、算法同学）的**轻量化工作台 Demo**。

项目覆盖从**问题发现 → 漏斗归因 → 实验设计 → AI 复盘建议**的完整分析闭环，帮助业务团队高效定位问题、验证策略、沉淀结论。

---

## 🏗️ 项目背景

内容电商平台增长不只是"拿流量"，推荐场景承接大量流量，是平台效率优化的关键位置。

平台常见的四类核心问题：

| 问题类型 | 表现 | 策略方向 |
|---------|------|---------|
| 高曝光低点击 | CTR 偏低，流量利用率不足 | 展示优化、内容表达、人群匹配 |
| 高点击低转化 | CVR 差，承接断层明显 | 详情优化、发券补贴、差异化策略 |
| 实验验证效率低 | 缺乏统一实验框架 | 标准化 A/B Test 设计助手 |
| 复盘协作不统一 | 结论理解不一致，缺少沉淀 | AI 结构化复盘模块 |

---

## 📐 产品结构

```
问题发现（Dashboard）
    ↓
漏斗归因（Funnel Analysis）
    ↓
策略验证（A/B Test Designer）
    ↓
结论沉淀（AI Review）
```

### 四个核心页面

| 页面 | 核心定位 | 主要输出 |
|------|---------|---------|
| 📊 **策略总览 Dashboard** | 集中展示核心指标与异常场景 | CTR/CVR/GMV 看板、趋势图、异常预警 |
| 🔍 **漏斗分析与归因页** | 链路拆解与问题精准定位 | 漏斗图、分群对比、前/后链路判断 |
| 🧪 **A/B Test 设计助手页** | 标准化实验方案自动生成 | 指标体系、分组方案、Markdown 文案 |
| 🤖 **AI 复盘与策略建议页** | 结构化复盘与放量建议 | 异常诊断、实验复盘、后续动作 |

---

## 📁 项目目录结构

```
ecommerce_workbench/
├── app.py                          # Streamlit 入口，首页说明与导航
├── requirements.txt                # 依赖清单
├── generate_data.py                # 模拟数据生成脚本
├── .env.example                    # API Key 配置示例
│
├── pages/
│   ├── 1_dashboard.py              # 策略总览 Dashboard
│   ├── 2_funnel_analysis.py        # 漏斗分析与归因页
│   ├── 3_abtest_designer.py        # A/B Test 设计助手页
│   └── 4_ai_review.py              # AI 复盘与策略建议页
│
├── modules/
│   ├── data_loader.py              # 统一数据读取模块
│   ├── metric_calculator.py        # 指标计算（CTR/CVR/GMV/ROI）
│   ├── filter_utils.py             # 统一筛选逻辑
│   ├── chart_builder.py            # Plotly 图表封装
│   ├── funnel_analyzer.py          # 漏斗分析与问题诊断
│   ├── abtest_generator.py         # 实验方案自动生成
│   └── ai_summary.py               # Claude API 调用与预设输出
│
└── data/
    └── clean_distribution_growth_analysis.csv   # 分析宽表（10万行）
```

---

## 📊 数据方案

### 分析宽表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| event_date | date | 事件日期（60天周期） |
| user_type | string | new_user / returning_user / high_potential_user |
| channel | string | recommendation_feed / search_result / campaign_page / store_page |
| content_type | string | short_video / live_clip / image_text |
| item_category | string | beauty / apparel / food / home / electronics / baby / sports |
| price_band | string | low / mid / high |
| impression | int | 曝光次数 |
| click | int | 点击次数 |
| detail_view | int | 详情页浏览次数 |
| add_to_cart | int | 加购次数 |
| order | int | 下单次数 |
| pay | int | 支付次数 |
| pay_amount | float | 支付金额（元） |
| campaign_cost | float | 策略成本（元） |
| experiment_group | string | control / treatment_a / treatment_b |
| is_new_payer | int | 是否新支付用户（0/1） |

### 数据特征
- **10万行**，覆盖 **60天** 时间周期（2026-01-16 ~ 2026-03-16）
- 包含真实业务规律：recommendation_feed CTR 偏低、高价格带转化率低、treatment 组效果显著等
- 漏斗单调性保证：impression ≥ click ≥ detail_view ≥ add_to_cart ≥ order ≥ pay

---

## 📈 指标口径

| 指标 | 英文名 | 计算口径 | 类型 |
|------|--------|---------|------|
| 点击率 | CTR | Click / Impression | 主指标 |
| 综合转化率 | CVR | Pay / Click | 主指标 |
| 成交金额 | GMV | Sum(pay_amount) | 主指标 |
| 详情浏览率 | Detail View Rate | Detail View / Click | 辅助指标 |
| 加购率 | Add to Cart Rate | Add to Cart / Detail View | 辅助指标 |
| 下单率 | Order Rate | Order / Add to Cart | 辅助指标 |
| 支付率 | Pay Rate | Pay / Order | 辅助指标 |
| 新客率 | New User Rate | New Paying Users / Total Paying Users | 辅助指标 |
| 投资回报率 | ROI | GMV / Campaign Cost | 护栏指标 |

---

## 🛠️ 技术栈

| 层次 | 技术 | 用途 |
|------|------|------|
| 前端框架 | **Streamlit** | 页面渲染与交互 |
| 数据处理 | **pandas** | 数据清洗、聚合计算 |
| 图表 | **Plotly** | 柱状图、折线图、漏斗图、热力图 |
| AI 调用 | **Claude API** (claude-opus-4-5) | 异常诊断与实验复盘 |
| 环境管理 | **python-dotenv** | API Key 等配置管理 |

---

## 🚀 本地运行方式

### 1. 克隆项目

```bash
git clone https://github.com/yunacong/电商平台分发增长与策略优化工作台.git
cd 电商平台分发增长与策略优化工作台
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key（可选）

```bash
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY
```

> 不配置 API Key 也可正常运行，AI 页面将展示预设的高质量示例输出。

### 4. 生成数据（已包含，可跳过）

```bash
python generate_data.py
```

### 5. 启动应用

```bash
streamlit run app.py
```

浏览器访问：**http://localhost:8501**

---

## ✨ 项目亮点

1. **平台侧视角**：从推荐分发效率切入，围绕 CTR/CVR/GMV/ROI 多目标平衡设计完整分析链路，而非泛泛的 AI 工具展示

2. **完整业务闭环**：问题发现 → 漏斗归因 → 实验设计 → AI 复盘，四个页面构成策略产品的完整工作流

3. **智能诊断**：自动识别前/后链路问题，输出结构化问题定位摘要，不依赖人工逐一比对

4. **A/B Test 标准化**：根据业务目标和策略类型自动推荐指标体系、分组方案、观察周期和风险提示，降低实验设计门槛

5. **AI 可插拔**：Claude API 接入真实模型，不可用时自动降级为预设示例输出，保证 Demo 完整性

6. **三位一体**：文档（Notion + README）+ 数据分析（模拟宽表 + 真实业务规律）+ Demo（可交互），体现从业务建模到系统落地的一体化能力

---

## 🔮 后续优化方向

- [ ] 增加 SQL 查询展示区（DuckDB）
- [ ] 支持下载实验方案为 Word/PDF
- [ ] 接入更多 AI Prompt 模板（分场景复盘）
- [ ] 增加更复杂的多维分群策略
- [ ] 部署为公开可访问的 Demo 链接（Streamlit Cloud）

---

