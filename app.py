import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px
from rapidfuzz import process

st.set_page_config(page_title="Teachers' Day Dashboard", layout="wide")
st.title("Teachers' Day Campaign Dashboard")

@st.cache_data(show_spinner=False)
def load_data(file):
    return pd.read_excel(file)

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

uploaded_file = st.file_uploader("Upload Excel file", type=[".xlsx"])

if uploaded_file:
    df = load_data(uploaded_file)

    # Basic Cleanup
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    # Fuzzy Match SBM and RBM if slight spelling differences
    sbm_col = "SBM Name"
    rbm_col = "RBM Name"
    df[sbm_col] = df[sbm_col].astype(str).str.strip().str.lower()
    df[rbm_col] = df[rbm_col].astype(str).str.strip().str.lower()

    unique_sbms = df[sbm_col].unique()
    unique_rbm = df[rbm_col].unique()

    sbm_mapping = {name: process.extractOne(name, unique_sbms)[0] for name in unique_sbms}
    rbm_mapping = {name: process.extractOne(name, unique_rbm)[0] for name in unique_rbm}

    df[sbm_col] = df[sbm_col].map(sbm_mapping)
    df[rbm_col] = df[rbm_col].map(rbm_mapping)

    # Filters
    state_list = sorted(df.get("Student Doctor's State", pd.Series(dtype='str')).dropna().unique())
    city_list = sorted(df.get("Student Doctor's City", pd.Series(dtype='str')).dropna().unique())
    sbm_list = sorted(df.get(sbm_col, pd.Series(dtype='str')).dropna().unique())
    rbm_list = sorted(df.get(rbm_col, pd.Series(dtype='str')).dropna().unique())

    state_filter = st.sidebar.multiselect("Filter by State", state_list)
    city_filter = st.sidebar.multiselect("Filter by City", city_list)
    sbm_filter = st.sidebar.multiselect("Filter by SBM", sbm_list)
    rbm_filter = st.sidebar.multiselect("Filter by RBM", rbm_list)

    filtered_df = df.copy()
    if state_filter:
        filtered_df = filtered_df[filtered_df["Student Doctor's State"].isin(state_filter)]
    if city_filter:
        filtered_df = filtered_df[filtered_df["Student Doctor's City"].isin(city_filter)]
    if sbm_filter:
        filtered_df = filtered_df[filtered_df[sbm_col].isin(sbm_filter)]
    if rbm_filter:
        filtered_df = filtered_df[filtered_df[rbm_col].isin(rbm_filter)]

    # Overall KPIs
    st.subheader("🔹 Overall Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Entries", len(filtered_df))
    col2.metric("Unique SBMs", filtered_df[sbm_col].nunique())
    col3.metric("Unique RBMs", filtered_df[rbm_col].nunique())

    # Prescriber Pie Chart
    st.subheader("🧠 Prescriber Type Distribution")
    if "Prescriber Type" in filtered_df.columns:
        pie_data = filtered_df["Prescriber Type"].value_counts().reset_index()
        pie_data.columns = ["Prescriber Type", "Count"]
        fig = px.pie(pie_data, names="Prescriber Type", values="Count", title="Prescriber Type")
        st.plotly_chart(fig, use_container_width=True)

    # Potential Pie
    st.subheader("🔥 Potential Classification")
    if "Potential" in filtered_df.columns:
        pot_data = filtered_df["Potential"].value_counts().reset_index()
        pot_data.columns = ["Potential", "Count"]
        fig2 = px.pie(pot_data, names="Potential", values="Count", title="Doctor Potential")
        st.plotly_chart(fig2, use_container_width=True)

    # RBM Performance by SBM
    st.subheader("📊 RBM-wise SBM Performance")
    group_perf = filtered_df.groupby([rbm_col, sbm_col]).size().reset_index(name='Responses')
    fig3 = px.bar(group_perf, x=sbm_col, y="Responses", color=rbm_col,
                  title="RBM-wise Responses based on SBM Performance")
    st.plotly_chart(fig3, use_container_width=True)

    # Doctor lists by Prescriber type and Potential
    st.subheader("📋 Doctor Lists")
    prescriber_options = filtered_df["Prescriber Type"].dropna().unique()
    selected_prescriber = st.multiselect("Select Prescriber Type", prescriber_options)

    potential_options = filtered_df["Potential"].dropna().unique()
    selected_potential = st.multiselect("Select Doctor Potential", potential_options)

    doc_df = filtered_df.copy()
    if selected_prescriber:
        doc_df = doc_df[doc_df["Prescriber Type"].isin(selected_prescriber)]
    if selected_potential:
        doc_df = doc_df[doc_df["Potential"].isin(selected_potential)]

    st.dataframe(doc_df[["Student Doctor's Name", "Prescriber Type", "Potential"]].dropna())

    # Download Final Data
    st.subheader("⬇️ Download Final Filtered Data")
    excel = to_excel(filtered_df)
    st.download_button(
        label="Download Excel",
        data=excel,
        file_name="filtered_teachers_day_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Please upload the Teachers' Day Excel file to begin.")
