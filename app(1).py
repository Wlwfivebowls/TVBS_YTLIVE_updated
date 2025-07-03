
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.title("📊 YouTube 直播頻道在線人數分析（工作表1 專用）")

# 指定工作表1，跳過前1行說明（實際從第2行開始是頻道資料）
sheet_url = "https://docs.google.com/spreadsheets/d/1DIz9Cd5iSr1ssNkyYgvBshwKcxfkdraOYilXbXzLXhU/gviz/tq?tqx=out:csv&sheet=工作表1"

@st.cache_data(ttl=300)
def load_data():
    try:
        raw = pd.read_csv(sheet_url, skiprows=1)
        raw = raw.dropna(how="all")  # 去除全空白列
        raw.columns = raw.iloc[0]  # 第2行實為標題
        df = raw.drop(raw.index[0])  # 去除標題列

        df.columns.values[0] = "頻道連結"
        df.columns.values[1] = "頻道名稱"
        df.columns.values[2] = "影片標題"

        id_cols = ["頻道連結", "頻道名稱", "影片標題"]
        value_cols = df.columns[3:]

        df_melted = df.melt(id_vars=id_cols, value_vars=value_cols, var_name="時間", value_name="在線人數")
        df_melted["時間"] = pd.to_datetime(df_melted["時間"], errors="coerce")
        df_melted["在線人數"] = pd.to_numeric(df_melted["在線人數"], errors="coerce")
        df_melted = df_melted.dropna(subset=["時間", "在線人數"])

        return df_melted
    except Exception as e:
        st.error(f"❌ 錯誤：{e}")
        return None

df = load_data()
if df is None or df.empty:
    st.stop()

channels = df["頻道名稱"].unique().tolist()
channels.sort()

選擇模式 = st.sidebar.radio("選擇檢視模式", ["單一頻道分析", "各頻道比較"])

if 選擇模式 == "單一頻道分析":
    selected_channel = st.sidebar.selectbox("請選擇頻道", channels)
    df = df[df["頻道名稱"] == selected_channel]

min_date, max_date = df["時間"].dt.date.min(), df["時間"].dt.date.max()
start_date = st.sidebar.date_input("開始日期", min_value=min_date, max_value=max_date, value=min_date)
end_date = st.sidebar.date_input("結束日期", min_value=min_date, max_value=max_date, value=max_date)

mask = (df["時間"].dt.date >= start_date) & (df["時間"].dt.date <= end_date)
df_filtered = df[mask].copy()
df_filtered["日期"] = df_filtered["時間"].dt.date
df_filtered["小時"] = df_filtered["時間"].dt.hour

grouped = df_filtered.groupby(["頻道名稱", "日期"])
stats = grouped["在線人數"].agg(
    每日平均="mean",
    每日加總="sum",
    午間平均=lambda x: x[(x.index.hour >= 11) & (x.index.hour < 14)].mean(),
    晚間平均=lambda x: x[(x.index.hour >= 19) & (x.index.hour < 22)].mean()
).reset_index()

均值 = stats.groupby("頻道名稱")[["每日平均", "午間平均", "晚間平均"]].mean().round().sort_values("每日平均", ascending=False)
均值.index.name = "頻道名稱"
st.subheader("📈 各頻道每日平均在線人數（排序）")

max_channel = 均值["每日平均"].idxmax()
均值["是否最高"] = ["✅" if name == max_channel else "" for name in 均值.index]
st.dataframe(均值.reset_index(), use_container_width=True)
.set_properties(**{"font-weight": "bold", "color": "black", "background-color": "#FFD700"}))

st.subheader("📅 每日在線人數統計表")
st.dataframe(stats.round(0), use_container_width=True)

if 選擇模式 == "各頻道比較":
    hourly_avg = df_filtered.groupby(["時間", "頻道名稱"])["在線人數"].mean().reset_index()
    chart = alt.Chart(hourly_avg).mark_line().encode(
        x="時間:T", y="在線人數:Q", color="頻道名稱:N", tooltip=["時間", "頻道名稱", "在線人數"]
    ).properties(width=700, height=400)
    st.altair_chart(chart, use_container_width=True)
