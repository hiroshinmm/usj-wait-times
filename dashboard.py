from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from database import init_db, query_all_history, query_attraction_list, query_history, query_latest

st.set_page_config(page_title="USJ 待ち時間ダッシュボード", page_icon="🎢", layout="wide")
init_db()

# ---- サイドバー ----
st.sidebar.title("設定")

period_options = {
    "今日": 0,
    "直近3日": 2,
    "直近1週間": 6,
    "直近1ヶ月": 29,
    "直近3ヶ月": 89,
}
period_label = st.sidebar.selectbox("表示期間", list(period_options.keys()))
days_back = period_options[period_label]

now_jst = datetime.now(timezone.utc) + timedelta(hours=9)
end_dt = datetime.now(timezone.utc)
start_dt = end_dt - timedelta(days=days_back)

auto_refresh = st.sidebar.toggle("自動更新 (5分ごと)", value=True)
if auto_refresh:
    st_autorefresh(interval=300_000, key="autorefresh")

st.sidebar.markdown("---")
st.sidebar.caption("データソース: [themeparks.wiki](https://themeparks.wiki)")

# ---- メインタイトル ----
st.title("🎢 USJ 待ち時間ダッシュボード")
st.caption(f"最終更新: {now_jst.strftime('%Y-%m-%d %H:%M')} JST")

# ---- 最新スナップショット ----
st.header("現在の待ち時間")
df_latest = query_latest()

if df_latest.empty:
    st.info("データがまだありません。`python collector.py` を起動して収集を開始してください。")
    st.stop()

df_operating = df_latest[df_latest["status"] == "OPERATING"].copy()
df_operating = df_operating.dropna(subset=["wait_minutes"])

if df_operating.empty:
    st.warning("現在営業中のアトラクションがありません（パーク閉園中の可能性があります）。")
else:
    def wait_color(minutes: float) -> str:
        if minutes < 20:
            return "#2ecc71"
        if minutes < 45:
            return "#f39c12"
        return "#e74c3c"

    df_operating = df_operating.sort_values("wait_minutes", ascending=True)
    colors = [wait_color(m) for m in df_operating["wait_minutes"]]

    fig_bar = go.Figure(
        go.Bar(
            x=df_operating["wait_minutes"],
            y=df_operating["attraction_name"],
            orientation="h",
            marker_color=colors,
            text=df_operating["wait_minutes"].astype(int).astype(str) + " 分",
            textposition="outside",
        )
    )
    fig_bar.update_layout(
        height=max(300, len(df_operating) * 28),
        xaxis_title="待ち時間 (分)",
        yaxis_title=None,
        margin=dict(l=10, r=80, t=20, b=40),
        plot_bgcolor="white",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("営業中", f"{len(df_operating)} アトラクション")
    col2.metric("最長待ち時間", f"{int(df_operating['wait_minutes'].max())} 分")
    col3.metric("平均待ち時間", f"{df_operating['wait_minutes'].mean():.0f} 分")

# ---- 時系列グラフ ----
st.header("待ち時間の推移")

attraction_df = query_attraction_list()
if not attraction_df.empty:
    selected_names = st.multiselect(
        "アトラクションを選択",
        options=attraction_df["attraction_name"].tolist(),
        default=attraction_df["attraction_name"].tolist()[:5],
    )

    if selected_names:
        selected_ids = attraction_df[attraction_df["attraction_name"].isin(selected_names)]["attraction_id"].tolist()
        frames = []
        for aid in selected_ids:
            df_h = query_history(aid, start_dt, end_dt)
            if not df_h.empty:
                name = attraction_df[attraction_df["attraction_id"] == aid]["attraction_name"].iloc[0]
                df_h["attraction_name"] = name
                df_h["fetched_at_jst"] = df_h["fetched_at"] + pd.Timedelta(hours=9)
                frames.append(df_h)

        if frames:
            df_trend = pd.concat(frames, ignore_index=True)
            fig_line = px.line(
                df_trend,
                x="fetched_at_jst",
                y="wait_minutes",
                color="attraction_name",
                labels={"fetched_at_jst": "時刻 (JST)", "wait_minutes": "待ち時間 (分)", "attraction_name": "アトラクション"},
                markers=True,
            )
            fig_line.update_layout(
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor="white",
                xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
                yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("選択期間内のデータがありません。")
    else:
        st.info("アトラクションを選択してください。")
else:
    st.info("アトラクションデータがありません。")

# ---- ヒートマップ ----
st.header("混雑ヒートマップ（時間帯 × アトラクション）")

df_all = query_all_history(start_dt, end_dt)
if not df_all.empty and df_all["wait_minutes"].notna().any():
    df_all["fetched_at_jst"] = df_all["fetched_at"] + pd.Timedelta(hours=9)
    df_all["hour"] = df_all["fetched_at_jst"].dt.hour

    pivot = (
        df_all.dropna(subset=["wait_minutes"])
        .groupby(["attraction_name", "hour"])["wait_minutes"]
        .mean()
        .round(1)
        .unstack(level="hour")
    )

    if not pivot.empty:
        fig_heat = px.imshow(
            pivot,
            labels=dict(x="時刻 (時)", y="アトラクション", color="平均待ち (分)"),
            color_continuous_scale="RdYlGn_r",
            aspect="auto",
        )
        fig_heat.update_layout(height=max(300, len(pivot) * 22))
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("ヒートマップ用のデータが不足しています。")
else:
    st.info("ヒートマップ用のデータが不足しています。")

# ---- 統計サマリー ----
st.header("統計サマリー")
if not df_all.empty and df_all["wait_minutes"].notna().any():
    summary = (
        df_all.dropna(subset=["wait_minutes"])
        .groupby("attraction_name")["wait_minutes"]
        .agg(平均=lambda x: round(x.mean(), 1), 最大="max", 最小="min", 計測回数="count")
        .reset_index()
        .rename(columns={"attraction_name": "アトラクション"})
        .sort_values("平均", ascending=False)
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)
else:
    st.info("統計データがありません。")

