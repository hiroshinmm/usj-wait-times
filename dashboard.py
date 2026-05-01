from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from database import init_db, query_all_history, query_attraction_list, query_history, query_latest

st.set_page_config(page_title="USJ 待ち時間ダッシュボード", page_icon="🎢", layout="wide")
init_db()

# ---- 粒度テーブル: (最大日数, resamplefreq, 表示ラベル) ----
_GRANULARITY = [
    (1,  "5min",  "5分単位"),
    (3,  "30min", "30分平均"),
    (7,  "1h",    "1時間平均"),
    (30, "3h",    "3時間平均"),
]


def _freq_for(days: int) -> str:
    return next((f for d, f, _ in _GRANULARITY if days <= d), "1D")


def _label_for(days: int) -> str:
    return next((l for d, _, l in _GRANULARITY if days <= d), "日次平均")


def resample_trend(df: pd.DataFrame, days: int) -> pd.DataFrame:
    freq = _freq_for(days)
    if freq == "5min":
        return df
    return (
        df.set_index("fetched_at_jst")
        .groupby("attraction_name")["wait_minutes"]
        .resample(freq)
        .mean()
        .round(1)
        .reset_index()
    )


# ---- 訪問予定アトラクションと日本語名マッピング ----
_DEFAULT_ATTRACTIONS = {
    "Mario Kart: Koopa's Challenge™",
    "JUJUTSU KAISEN: The Real 4-D — Clock Tower of Recurrence",
    "Detective Conan 4-D Live Show: Jewel Under the Starry Sky",
    "Space Fantasy - The Ride",
    "Jurassic Park - The Ride",
    "Despicable Me: Minion Mayhem",
    "Illumination's Villain-Con Minion Blast",
    "JAWS",
    "Harry Potter and the Forbidden Journey™",
    "Flight of the Hippogriff™",
    "Hollywood Dream - The Ride",
    "Mine Cart Madness™",
}

_JA_NAMES = {
    # 訪問予定
    "Mario Kart: Koopa's Challenge™":                           "マリオカート〜クッパの挑戦状〜™",
    "JUJUTSU KAISEN: The Real 4-D — Clock Tower of Recurrence": "呪術廻戦 ザ・リアル4-D〜廻轉の時計塔〜",
    "Detective Conan 4-D Live Show: Jewel Under the Starry Sky": "名探偵コナン4-Dライブショー",
    "Space Fantasy - The Ride":                                 "スペース・ファンタジー・ザ・ライド",
    "Jurassic Park - The Ride":                                 "ジュラシック・パーク・ザ・ライド",
    "Despicable Me: Minion Mayhem":                             "ミニオン・ハチャメチャ・ライド",
    "Illumination's Villain-Con Minion Blast":                  "ヴィランコン・ミニオン・ブラスト",
    "JAWS":                                                     "ジョーズ",
    "Harry Potter and the Forbidden Journey™":                  "ハリー・ポッター・アンド・ザ・フォービドゥン・ジャーニー™",
    "Flight of the Hippogriff™":                                "フライト・オブ・ザ・ヒッポグリフ™",
    "Hollywood Dream - The Ride":                               "ハリウッド・ドリーム・ザ・ライド",
    "Mine Cart Madness™":                                       "ドンキーコング・カントリー マインカート・マッドネス™",
    # その他
    "Abby's Magical Party":                                     "アビーのマジカル・パーティー",
    "Abby's Magical Tree":                                      "アビーのマジカル・ツリー",
    "Amity Boardwalk Games":                                    "アミティ・ボードウォーク・ゲームズ",
    "Banana Cabana":                                            "バナナ・カバナ",
    "Bert & Ernie Prop Shop Game Place":                        "バート＆アーニー プロップ・ショップ・ゲームプレイス",
    "Bert and Ernie's Wonder: The Sea":                         "バートとアーニーのワンダー・ザ・シー",
    "Big Bird's Big Nest":                                      "ビッグバードのビッグ・ネスト",
    "Big Bird's Big Top Circus":                                "ビッグバードのビッグトップ・サーカス",
    "Cookie Monster Slide":                                     "クッキーモンスター・スライド",
    "Elmo's Bubble Bubble":                                     "エルモのバブルバブル",
    "Elmo's Go-Go Skateboard":                                  "エルモのゴーゴー・スケートボード",
    "Elmo's Little Drive":                                      "エルモのリトル・ドライブ",
    "Ernie's Rubber Duckie Race":                               "アーニーのゴム・アヒルレース",
    "Festival In The Park":                                     "フェスティバル・イン・ザ・パーク",
    "Freeze Ray Sliders":                                       "フリーズ・レイ・スライダーズ",
    "Grover's Construction Company":                            "グローバーのコンストラクション・カンパニー",
    "Hello Kitty's Cupcake Dream":                              "ハローキティのカップケーキ・ドリーム",
    "Hollywood Dream - The Ride: Backdrop":                     "ハリウッド・ドリーム・ザ・ライド〜バックドロップ〜",
    "Moppy's Balloon Trip":                                     "モッピーのバルーン・トリップ",
    "Power-Up Band™ Key Challenges":                            "パワーアップバンド™ キーチャレンジ",
    "Sesame's Big Drive":                                       "セサミのビッグ・ドライブ",
    "Snoopy's Flying Ace Adventure":                            "スヌーピーのグレート・レース",
    "Space Fantasy - The Ride: CLUB ZEDD REMIX":                "スペース・ファンタジー・ザ・ライド：クラブZEDDリミックス",
    "Space Killer":                                             "スペース・キラー",
    "The Flying Dinosaur":                                      "ザ・フライング・ダイナソー",
    "The Flying Snoopy":                                        "ザ・フライング・スヌーピー",
    "Water Garden":                                             "ウォーター・ガーデン",
    "Yoshi's Adventure™":                                       "ヨッシー・アドベンチャー™",
    # ショー
    "Jurassic World Baby Dino Adventure":                       "ジュラシック・ワールド・ベイビー・ダイノ・アドベンチャー",
    "Jurassic World Raptor Alert":                              "ジュラシック・ワールド・ラプター・アラート",
    "Meet the Hogsmeade Magical Creatures":                     "ミート・ザ・ホグズミード・マジカル・クリーチャーズ",
    "WaterWorld":                                               "ウォーターワールド",
}

# ---- サイドバー ----
st.sidebar.title("設定")

auto_refresh = st.sidebar.toggle("自動更新 (5分ごと)", value=True)
if auto_refresh:
    st_autorefresh(interval=300_000, key="autorefresh")

st.sidebar.markdown("---")

today_jst = (datetime.now(timezone.utc) + timedelta(hours=9)).date()

date_range = st.sidebar.date_input(
    "表示期間",
    value=(today_jst, today_jst),
    max_value=today_jst,
)

if isinstance(date_range, (list, tuple)):
    start_date = date_range[0]
    end_date = date_range[-1]
else:
    start_date = end_date = date_range

days_diff = (end_date - start_date).days + 1

# JST日付 → UTC datetime（DBはUTC保存）
start_dt = datetime.combine(start_date, datetime.min.time()) - timedelta(hours=9)
end_dt   = datetime.combine(end_date,   datetime.max.time()) - timedelta(hours=9)

# アトラクション選択（チェックボックス）
st.sidebar.markdown("---")
st.sidebar.markdown("**アトラクション**")
attraction_df = query_attraction_list()
all_names = attraction_df["attraction_name"].tolist() if not attraction_df.empty else []

col_a, col_b = st.sidebar.columns(2)
if col_a.button("全選択", use_container_width=True):
    for n in all_names:
        st.session_state[f"cb_{n}"] = True
if col_b.button("全解除", use_container_width=True):
    for n in all_names:
        st.session_state[f"cb_{n}"] = False

planned = [n for n in all_names if n in _DEFAULT_ATTRACTIONS]
others  = [n for n in all_names if n not in _DEFAULT_ATTRACTIONS]

selected_names = []
st.sidebar.markdown("**訪問予定**")
for n in planned:
    label = _JA_NAMES.get(n, n)
    if st.sidebar.checkbox(label, value=True, key=f"cb_{n}"):
        selected_names.append(n)

st.sidebar.markdown("**その他**")
for n in others:
    label = _JA_NAMES.get(n, n)
    if st.sidebar.checkbox(label, value=False, key=f"cb_{n}"):
        selected_names.append(n)

st.sidebar.markdown("---")
st.sidebar.caption("データソース: [themeparks.wiki](https://themeparks.wiki)")

# ---- メインタイトル ----
now_jst = datetime.now(timezone.utc) + timedelta(hours=9)
st.title("🎢 USJ 待ち時間ダッシュボード")
st.caption(f"最終更新: {now_jst.strftime('%Y-%m-%d %H:%M')} JST")

# ---- 現在の待ち時間 ----
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

# ---- 待ち時間の推移 ----
granularity = _label_for(days_diff)
st.header(f"待ち時間の推移　（{granularity}）")

if not selected_names:
    st.info("サイドバーでアトラクションを選択してください。")
elif attraction_df.empty:
    st.info("アトラクションデータがありません。")
else:
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
        df_trend = resample_trend(pd.concat(frames, ignore_index=True), days_diff)
        show_markers = days_diff <= 1
        fig_line = px.line(
            df_trend,
            x="fetched_at_jst",
            y="wait_minutes",
            color="attraction_name",
            labels={
                "fetched_at_jst": "時刻 (JST)",
                "wait_minutes": "待ち時間 (分)",
                "attraction_name": "アトラクション",
            },
            markers=show_markers,
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

# ---- 混雑ヒートマップ ----
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
