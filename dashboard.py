import streamlit as st
import sqlite3
import pandas as pd

DB_PATH = "scraper/indicators.db"

st.set_page_config(page_title="Argentina Economic Dashboard", layout="wide")
st.title("🇦🇷 Argentina Economic Indicators")

def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM indicators ORDER BY date DESC", conn)
    conn.close()
    return df

df = load_data()

if df.empty:
    st.warning("No data available. Run the scraper first.")
else:
    st.subheader("Latest Indicators")
    latest = df.groupby("name").first().reset_index()
    st.dataframe(latest[["name", "value", "date", "source"]])

    st.subheader("Trends")
    indicator = st.selectbox("Select indicator:", df["name"].unique())
    series = df[df["name"] == indicator].sort_values("date")
    st.line_chart(series.set_index("date")["value"])
