"""
生成真实感强的模拟分析数据集
覆盖 60 天、约 10 万行数据，包含完整漏斗链路、实验组差异、分群差异等
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)

# ── 基础参数 ──────────────────────────────────────────────────────────────────
N_ROWS = 100_000
START_DATE = datetime(2026, 1, 16)
END_DATE   = datetime(2026, 3, 16)

CHANNELS       = ["recommendation_feed", "search_result", "campaign_page", "store_page"]
USER_TYPES     = ["new_user", "returning_user", "high_potential_user"]
AGE_GROUPS     = ["18-24", "25-34", "35-44", "45+"]
GENDERS        = ["female", "male"]
CITY_TIERS     = ["tier1", "tier2", "tier3"]
CONTENT_TYPES  = ["short_video", "live_clip", "image_text"]
ITEM_CATS      = ["beauty", "apparel", "food", "home", "electronics", "baby", "sports"]
PRICE_BANDS    = ["low", "mid", "high"]
EXP_GROUPS     = ["control", "treatment_a", "treatment_b"]
STRATEGY_TYPES = ["display_optimization", "ranking_adjustment", "detail_optimization",
                  "coupon", "subsidy", "reactivation_push"]

# ── 日期生成 ──────────────────────────────────────────────────────────────────
date_range = pd.date_range(START_DATE, END_DATE)
dates = np.random.choice(date_range, N_ROWS)

# ── 维度字段 ──────────────────────────────────────────────────────────────────
channel_probs = [0.45, 0.25, 0.20, 0.10]   # rec_feed 最大
channels = np.random.choice(CHANNELS, N_ROWS, p=channel_probs)

user_probs = [0.35, 0.50, 0.15]
user_types = np.random.choice(USER_TYPES, N_ROWS, p=user_probs)

age_groups = np.random.choice(AGE_GROUPS, N_ROWS, p=[0.25, 0.40, 0.25, 0.10])
genders    = np.random.choice(GENDERS,    N_ROWS, p=[0.55, 0.45])
city_tiers = np.random.choice(CITY_TIERS, N_ROWS, p=[0.30, 0.40, 0.30])

content_probs = [0.50, 0.35, 0.15]
content_types = np.random.choice(CONTENT_TYPES, N_ROWS, p=content_probs)

item_cats   = np.random.choice(ITEM_CATS,   N_ROWS)
price_bands = np.random.choice(PRICE_BANDS, N_ROWS, p=[0.45, 0.35, 0.20])

# 实验组：前30天主要是control，后期引入treatment
exp_probs = np.where(
    dates < np.datetime64(datetime(2026, 2, 16)),
    0, 1
)
exp_groups = []
for i in range(N_ROWS):
    if dates[i] < np.datetime64(datetime(2026, 2, 16)):
        exp_groups.append("control")
    else:
        exp_groups.append(np.random.choice(EXP_GROUPS, p=[0.40, 0.35, 0.25]))

exp_groups = np.array(exp_groups)

# 实验组对应策略类型
strategy_map = {
    "control":     "display_optimization",
    "treatment_a": "ranking_adjustment",
    "treatment_b": "coupon",
}
strategy_types = np.array([strategy_map[eg] for eg in exp_groups])

# ── 漏斗指标生成（含真实业务规律） ───────────────────────────────────────────

def base_impression():
    return np.random.randint(500, 5000, N_ROWS)

impression = base_impression()

# ── CTR 基准：按 channel / content_type / user_type 差异化 ──
ctr_base = np.full(N_ROWS, 0.055)

# channel 影响
ctr_base = np.where(channels == "recommendation_feed", ctr_base * 0.90, ctr_base)  # rec_feed CTR 偏低（高曝光低点击问题）
ctr_base = np.where(channels == "search_result",       ctr_base * 1.20, ctr_base)
ctr_base = np.where(channels == "campaign_page",       ctr_base * 1.10, ctr_base)
ctr_base = np.where(channels == "store_page",          ctr_base * 0.95, ctr_base)

# content_type 影响
ctr_base = np.where(content_types == "short_video",  ctr_base * 1.15, ctr_base)
ctr_base = np.where(content_types == "live_clip",    ctr_base * 1.05, ctr_base)
ctr_base = np.where(content_types == "image_text",   ctr_base * 0.85, ctr_base)

# user_type 影响
ctr_base = np.where(user_types == "new_user",           ctr_base * 0.92, ctr_base)
ctr_base = np.where(user_types == "high_potential_user",ctr_base * 1.18, ctr_base)

# 实验组影响（treatment_a 展示优化 → 提升 CTR）
ctr_base = np.where(exp_groups == "treatment_a", ctr_base * 1.12, ctr_base)
ctr_base = np.where(exp_groups == "treatment_b", ctr_base * 1.05, ctr_base)

# 时间趋势：后期略有提升
date_numeric = (pd.to_datetime(dates) - pd.Timestamp(START_DATE)).days.values
time_factor  = 1 + date_numeric / 700
ctr_base     = ctr_base * time_factor

# 加噪
ctr = np.clip(ctr_base + np.random.normal(0, 0.008, N_ROWS), 0.015, 0.25)
click = np.round(impression * ctr).astype(int)
click = np.minimum(click, impression)

# ── Detail View Rate ───────────────────────────────────────────────────────
dvr_base = np.full(N_ROWS, 0.62)
dvr_base = np.where(content_types == "short_video", dvr_base * 1.05, dvr_base)
dvr_base = np.where(channels == "campaign_page",    dvr_base * 1.08, dvr_base)
dvr_base = np.where(user_types == "new_user",       dvr_base * 0.90, dvr_base)
dvr_base = np.where(exp_groups == "treatment_b",    dvr_base * 1.06, dvr_base)
dvr  = np.clip(dvr_base + np.random.normal(0, 0.05, N_ROWS), 0.25, 0.95)
detail_view = np.round(click * dvr).astype(int)
detail_view = np.minimum(detail_view, click)

# ── Add to Cart Rate ───────────────────────────────────────────────────────
acr_base = np.full(N_ROWS, 0.38)
acr_base = np.where(price_bands == "high",              acr_base * 0.70, acr_base)
acr_base = np.where(price_bands == "low",               acr_base * 1.10, acr_base)
acr_base = np.where(user_types == "new_user",           acr_base * 0.82, acr_base)
acr_base = np.where(user_types == "high_potential_user",acr_base * 1.20, acr_base)
acr_base = np.where(item_cats == "beauty",              acr_base * 1.12, acr_base)
acr_base = np.where(item_cats == "electronics",         acr_base * 0.78, acr_base)
acr_base = np.where(exp_groups == "treatment_b",        acr_base * 1.08, acr_base)  # 优惠券 → 提升加购
acr  = np.clip(acr_base + np.random.normal(0, 0.05, N_ROWS), 0.05, 0.85)
add_to_cart = np.round(detail_view * acr).astype(int)
add_to_cart = np.minimum(add_to_cart, detail_view)

# ── Order Rate ─────────────────────────────────────────────────────────────
or_base = np.full(N_ROWS, 0.72)
or_base = np.where(price_bands == "high",              or_base * 0.78, or_base)
or_base = np.where(user_types == "high_potential_user",or_base * 1.10, or_base)
or_base = np.where(exp_groups == "treatment_b",        or_base * 1.05, or_base)
order_r = np.clip(or_base + np.random.normal(0, 0.06, N_ROWS), 0.20, 0.98)
order   = np.round(add_to_cart * order_r).astype(int)
order   = np.minimum(order, add_to_cart)

# ── Pay Rate ───────────────────────────────────────────────────────────────
pr_base = np.full(N_ROWS, 0.82)
pr_base = np.where(price_bands == "high",              pr_base * 0.80, pr_base)
pr_base = np.where(user_types == "new_user",           pr_base * 0.85, pr_base)
pr_base = np.where(user_types == "high_potential_user",pr_base * 1.08, pr_base)
pr_base = np.where(exp_groups == "treatment_b",        pr_base * 1.06, pr_base)
pay_r   = np.clip(pr_base + np.random.normal(0, 0.05, N_ROWS), 0.20, 0.99)
pay     = np.round(order * pay_r).astype(int)
pay     = np.minimum(pay, order)

# ── Pay Amount ─────────────────────────────────────────────────────────────
avg_price_map = {"low": 35, "mid": 150, "high": 680}
avg_prices = np.array([avg_price_map[pb] for pb in price_bands], dtype=float)
cat_multiplier = {"beauty": 1.2, "apparel": 1.0, "food": 0.6, "home": 1.4,
                  "electronics": 2.5, "baby": 1.1, "sports": 1.3}
cat_mult = np.array([cat_multiplier[ic] for ic in item_cats])
pay_amount = np.where(
    pay > 0,
    pay * avg_prices * cat_mult * np.random.lognormal(0, 0.25, N_ROWS),
    0.0
)
pay_amount = np.round(pay_amount, 2)

# ── Campaign Cost ──────────────────────────────────────────────────────────
cost_base = pay_amount * np.random.uniform(0.08, 0.18, N_ROWS)
cost_base = np.where(exp_groups == "treatment_b", cost_base * 1.35, cost_base)  # 优惠券成本更高
cost_base = np.where(exp_groups == "control",     cost_base * 0.90, cost_base)
campaign_cost = np.round(np.maximum(cost_base, 0), 2)

# ── is_new_payer ───────────────────────────────────────────────────────────
is_new_payer = np.where(
    (pay > 0) & (user_types == "new_user"),
    np.random.binomial(1, 0.75, N_ROWS),
    np.where(pay > 0, np.random.binomial(1, 0.12, N_ROWS), 0)
)

# ── user_id / item_id ──────────────────────────────────────────────────────
user_ids = [f"u_{np.random.randint(100000, 999999)}" for _ in range(N_ROWS)]
item_ids = [f"i_{np.random.randint(10000, 99999)}"   for _ in range(N_ROWS)]

# ── 组装 DataFrame ─────────────────────────────────────────────────────────
df = pd.DataFrame({
    "event_date":       pd.to_datetime(dates).date,
    "user_id":          user_ids,
    "user_type":        user_types,
    "age_group":        age_groups,
    "gender":           genders,
    "city_tier":        city_tiers,
    "item_id":          item_ids,
    "item_category":    item_cats,
    "price_band":       price_bands,
    "content_type":     content_types,
    "channel":          channels,
    "impression":       impression,
    "click":            click,
    "detail_view":      detail_view,
    "add_to_cart":      add_to_cart,
    "order":            order,
    "pay":              pay,
    "pay_amount":       pay_amount,
    "campaign_cost":    campaign_cost,
    "experiment_group": exp_groups,
    "strategy_type":    strategy_types,
    "is_new_payer":     is_new_payer,
})

# 保证漏斗单调性
for col_pair in [("click","impression"),("detail_view","click"),
                 ("add_to_cart","detail_view"),("order","add_to_cart"),("pay","order")]:
    df[col_pair[0]] = np.minimum(df[col_pair[0]], df[col_pair[1]])

df["event_date"] = pd.to_datetime(df["event_date"])
df = df.sort_values("event_date").reset_index(drop=True)

out_path = "data/clean_distribution_growth_analysis.csv"
df.to_csv(out_path, index=False)
print(f"✅ 数据生成完成: {len(df):,} 行 → {out_path}")
print(df.describe().T[["mean","std","min","max"]])
