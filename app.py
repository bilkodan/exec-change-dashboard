import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(layout="wide")

st.title("🚨 Exec Change Intelligence Dashboard")

conn = sqlite3.connect("exec_changes.db", check_same_thread=False)

try:
    df = pd.read_sql("SELECT * FROM changes ORDER BY filed_at DESC", conn)
except:
    df = pd.DataFrame()

st.metric("Total Events", len(df))

st.subheader("Latest Executive Changes")

if len(df) > 0:
    st.dataframe(df, use_container_width=True)
else:
    st.info("No data yet. Worker is still running.")
