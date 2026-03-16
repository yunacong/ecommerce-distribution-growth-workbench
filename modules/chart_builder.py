"""
chart_builder.py — 图表构建模块（Plotly）

职责：封装 Plotly 图表构建，统一风格。
颜色规范：主色 #1E5799，强调 #2E86AB，异常红 #E74C3C，绿 #27AE60，背景 #F5F7FA
"""
from __future__ import annotations
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# ── 颜色规范 ──────────────────────────────────────────────────────────────────
PRIMARY    = "#1E5799"
SECONDARY  = "#2E86AB"
ACCENT     = "#4ECDC4"
DANGER     = "#E74C3C"
SUCCESS    = "#27AE60"
WARNING    = "#F39C12"
LIGHT_BG   = "#F5F7FA"
GRAY       = "#95A5A6"

COLOR_SEQ  = [PRIMARY, SECONDARY, ACCENT, "#A8DADC", "#457B9D", "#1D3557"]

LAYOUT_DEFAULTS = dict(
    paper_bgcolor=LIGHT_BG,
    plot_bgcolor="white",
    font=dict(family="PingFang SC, Microsoft YaHei, sans-serif", size=12, color="#2C3E50"),
    margin=dict(l=40, r=20, t=50, b=40),
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def _apply_layout(fig: go.Figure, title: str = "", height: int = 380, **kwargs) -> go.Figure:
    layout = {**LAYOUT_DEFAULTS, "title": dict(text=title, font=dict(size=14, color="#2C3E50")), "height": height}
    layout.update(kwargs)
    fig.update_layout(**layout)
    return fig


# ── 核心图表函数 ───────────────────────────────────────────────────────────────

def build_trend_line_chart(
    df: pd.DataFrame,
    x: str,
    y_cols: list[str],
    y_labels: dict | None = None,
    title: str = "",
    height: int = 360,
    y_format: str = "percent",
) -> go.Figure:
    """折线趋势图（支持多指标双轴）。

    Args:
        df: 含 x 列和 y_cols 列的 DataFrame
        x: x 轴字段名
        y_cols: y 轴字段名列表（最多2个，第2个用右轴）
        y_labels: 字段名 → 显示标签的映射
        title: 图表标题
        height: 图表高度
        y_format: "percent" | "number" | "currency"

    Returns:
        go.Figure
    """
    if y_labels is None:
        y_labels = {}

    fig = go.Figure()
    colors = [PRIMARY, DANGER, SECONDARY, WARNING]

    for i, col in enumerate(y_cols):
        label = y_labels.get(col, col)
        is_right = i == 1 and len(y_cols) > 1
        yaxis = "y2" if is_right else "y"

        if y_format == "percent":
            text_vals = [f"{v*100:.2f}%" for v in df[col]]
        elif y_format == "currency":
            text_vals = [f"¥{v/10000:.1f}万" for v in df[col]]
        else:
            text_vals = [f"{v:.2f}" for v in df[col]]

        fig.add_trace(go.Scatter(
            x=df[x], y=df[col],
            name=label,
            mode="lines+markers",
            line=dict(color=colors[i % len(colors)], width=2.5),
            marker=dict(size=5),
            yaxis=yaxis,
            hovertemplate=f"<b>{label}</b><br>日期: %{{x|%Y-%m-%d}}<br>值: %{{text}}<extra></extra>",
            text=text_vals,
        ))

    layout_extra = {}
    if len(y_cols) > 1:
        layout_extra["yaxis2"] = dict(
            overlaying="y", side="right",
            showgrid=False,
            tickformat=".2%" if y_format == "percent" else ".2f",
        )

    if y_format == "percent":
        layout_extra["yaxis"] = dict(tickformat=".2%", gridcolor="#E8EDF0")
    elif y_format == "currency":
        layout_extra["yaxis"] = dict(tickformat=",.0f", gridcolor="#E8EDF0")
    else:
        layout_extra["yaxis"] = dict(gridcolor="#E8EDF0")

    _apply_layout(fig, title=title, height=height, **layout_extra)
    fig.update_xaxes(showgrid=False)
    return fig


def build_metric_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color_col: str | None = None,
    height: int = 360,
    y_format: str = "percent",
    global_avg: float | None = None,
    show_values: bool = True,
) -> go.Figure:
    """柱状图（支持全局均值参考线、异常标色）。

    Args:
        df: 数据
        x: x 轴字段
        y: y 轴字段
        title: 标题
        color_col: 颜色分组字段（可选）
        height: 高度
        y_format: "percent" | "number" | "currency"
        global_avg: 全局均值（用于画参考线和异常标色）
        show_values: 是否在柱上显示数值

    Returns:
        go.Figure
    """
    fig = go.Figure()

    if y_format == "percent":
        fmt_fn = lambda v: f"{v*100:.2f}%"
        tick_fmt = ".1%"
    elif y_format == "currency":
        fmt_fn = lambda v: f"¥{v/10000:.1f}万"
        tick_fmt = ",.0f"
    else:
        fmt_fn = lambda v: f"{v:.2f}"
        tick_fmt = ".2f"

    # 颜色：异常标红
    if global_avg is not None:
        bar_colors = [DANGER if v < global_avg * 0.9 else PRIMARY for v in df[y]]
    else:
        bar_colors = [COLOR_SEQ[i % len(COLOR_SEQ)] for i in range(len(df))]

    text_vals = [fmt_fn(v) for v in df[y]] if show_values else None

    fig.add_trace(go.Bar(
        x=df[x], y=df[y],
        marker_color=bar_colors,
        text=text_vals,
        textposition="outside",
        hovertemplate=f"<b>%{{x}}</b><br>{y}: %{{text}}<extra></extra>",
    ))

    if global_avg is not None:
        fig.add_hline(
            y=global_avg,
            line_dash="dash",
            line_color=WARNING,
            annotation_text=f"均值 {fmt_fn(global_avg)}",
            annotation_position="top right",
        )

    _apply_layout(fig, title=title, height=height,
                  yaxis=dict(tickformat=tick_fmt, gridcolor="#E8EDF0"),
                  showlegend=False)
    fig.update_xaxes(showgrid=False)
    return fig


def build_funnel_chart(
    stages: list[str],
    values: list[int | float],
    title: str = "全局漏斗",
    height: int = 420,
) -> go.Figure:
    """漏斗图。

    Args:
        stages: 漏斗环节标签列表
        values: 各环节数量列表
        title: 标题
        height: 高度

    Returns:
        go.Figure
    """
    n = len(stages)
    funnel_colors = [
        f"rgba(30,87,153,{1.0 - i*0.12})" for i in range(n)
    ]

    # 计算环比转化率
    conv_rates = []
    for i in range(n):
        if i == 0:
            conv_rates.append("100%")
        else:
            rate = values[i] / values[i-1] * 100 if values[i-1] > 0 else 0
            conv_rates.append(f"{rate:.1f}%")

    text_labels = [
        f"{s}<br>{v:,.0f} ({r})" for s, v, r in zip(stages, values, conv_rates)
    ]

    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textinfo="value+percent previous",
        marker=dict(color=funnel_colors),
        connector=dict(line=dict(color="#BDC3C7", dash="dot", width=1)),
        hovertemplate="<b>%{y}</b><br>数量: %{x:,.0f}<br>相对上一环节: %{percentPrevious:.1%}<extra></extra>",
    ))

    _apply_layout(fig, title=title, height=height, showlegend=False)
    return fig


def build_grouped_bar_chart(
    df: pd.DataFrame,
    x: str,
    y_cols: list[str],
    y_labels: dict | None = None,
    title: str = "",
    height: int = 380,
    y_format: str = "percent",
) -> go.Figure:
    """分组柱状图（多指标对比）。

    Args:
        df: 数据
        x: x 轴字段
        y_cols: y 轴字段列表
        y_labels: 字段 → 标签映射
        title: 标题
        height: 高度
        y_format: "percent" | "number" | "currency"

    Returns:
        go.Figure
    """
    if y_labels is None:
        y_labels = {}

    if y_format == "percent":
        fmt_fn = lambda v: f"{v*100:.2f}%"
        tick_fmt = ".1%"
    elif y_format == "currency":
        fmt_fn = lambda v: f"¥{v/10000:.1f}万"
        tick_fmt = ",.0f"
    else:
        fmt_fn = lambda v: f"{v:.2f}"
        tick_fmt = ".2f"

    fig = go.Figure()
    for i, col in enumerate(y_cols):
        label = y_labels.get(col, col)
        fig.add_trace(go.Bar(
            name=label,
            x=df[x],
            y=df[col],
            marker_color=COLOR_SEQ[i % len(COLOR_SEQ)],
            text=[fmt_fn(v) for v in df[col]],
            textposition="outside",
            hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{text}}<extra></extra>",
        ))

    fig.update_layout(barmode="group")
    _apply_layout(fig, title=title, height=height,
                  yaxis=dict(tickformat=tick_fmt, gridcolor="#E8EDF0"))
    fig.update_xaxes(showgrid=False)
    return fig


def build_heatmap(
    df_pivot: pd.DataFrame,
    title: str = "",
    height: int = 350,
    fmt: str = ".2%",
) -> go.Figure:
    """热力图（用于分群×指标的可视化）。

    Args:
        df_pivot: 行为维度值、列为指标的 pivot 表
        title: 标题
        height: 高度
        fmt: 数值格式

    Returns:
        go.Figure
    """
    z = df_pivot.values
    text_vals = [[f"{v:{fmt}}" if not pd.isna(v) else "N/A" for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=df_pivot.columns.tolist(),
        y=df_pivot.index.tolist(),
        text=text_vals,
        texttemplate="%{text}",
        colorscale=[[0, "#EBF5FB"], [0.5, "#2E86AB"], [1, "#1D3557"]],
        hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>值: %{text}<extra></extra>",
        showscale=True,
    ))
    _apply_layout(fig, title=title, height=height, showlegend=False)
    return fig


def build_scatter_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    size: str | None = None,
    color: str | None = None,
    title: str = "",
    height: int = 380,
    x_label: str = "",
    y_label: str = "",
) -> go.Figure:
    """散点图（气泡图）。

    Args:
        df: 数据
        x: x 轴字段
        y: y 轴字段
        size: 气泡大小字段（可选）
        color: 颜色分组字段（可选）
        title: 标题
        height: 高度
        x_label / y_label: 轴标签

    Returns:
        go.Figure
    """
    fig = px.scatter(
        df, x=x, y=y,
        size=size,
        color=color,
        color_discrete_sequence=COLOR_SEQ,
        labels={x: x_label or x, y: y_label or y},
        hover_data=df.columns.tolist(),
    )
    _apply_layout(fig, title=title, height=height)
    return fig
