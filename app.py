import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import base64
from rapidfuzz import process

st.set_page_config(layout="wide")
st.title("📊 Teachers' Day Campaign Dashboard")

@st.cache_data
def load_data(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()  # Remove leading/trailing spaces
    df.columns = df.columns.str.replace("’", "'")  # Replace curly quotes with straight quotes
    return df

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

def download_button(df):
    excel = to_excel(df)
    b64 = base64.b64encode(excel).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="filtered_data.xlsx">📥 Download Excel</a>'
    return href

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = load_data(uploaded_file)

    # SIDEBAR FILTERS
    st.sidebar.header("🔍 Filters")

    state_column = "Student Doctor's State"
    state_options = []
    if state_column in df.columns:
        state_options = sorted(df[state_column].dropna().unique())

    state_filter = st.sidebar.multiselect("Filter by State", state_options)
    sbm_filter = st.sidebar.text_input("Search SBM Name")
    rbm_filter = st.sidebar.text_input("Search RBM Name")

    # APPLY FILTERS
    if state_filter and state_column in df.columns:
        df = df[df[state_column].isin(state_filter)]
    if sbm_filter and "SBM Name" in df.columns:
        df = df[df["SBM Name"].str.contains(sbm_filter, case=False, na=False)]
    if rbm_filter and "RBM Name" in df.columns:
        df = df[df["RBM Name"].str.contains(rbm_filter, case=False, na=False)]

    # MAIN KPI METRICS
    st.subheader("📌 Campaign Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Entries", len(df))
    col2.metric("Unique SBMs", df["SBM Name"].nunique() if "SBM Name" in df.columns else 0)
    col3.metric("Unique RBMs", df["RBM Name"].nunique() if "RBM Name" in df.columns else 0)

    # PIE CHART: Prescriber Type
    st.subheader("🔄 Prescriber Type Distribution")
    if "Prescriber Type" in df.columns:
        fig1 = px.pie(df, names="Prescriber Type", title="Prescriber Type Breakdown")
        st.plotly_chart(fig1, use_container_width=True)

    # PIE CHART: Potential
    st.subheader("📈 Doctor Potential Distribution")
    if "Potential" in df.columns:
        fig2 = px.pie(df, names="Potential", title="Doctor Potential")
        st.plotly_chart(fig2, use_container_width=True)

    # RBM-to-SBM Drilldown
    st.subheader("👥 RBM-wise & SBM-wise Summary")
    if "RBM Name" in df.columns and "SBM Name" in df.columns:
        grouped = df.groupby(["RBM Name", "SBM Name"]).size().reset_index(name="Entries")
        st.dataframe(grouped)

    # TABLES FOR PRESCRIBER TYPE
    st.subheader("🩺 Doctors by Prescriber Type")
    if "Prescriber Type" in df.columns:
        for pt in ["Regular", "Occasional", "Non-Prescriber"]:
            st.markdown(f"**{pt} Doctors:**")
            filtered = df[df["Prescriber Type"] == pt]
            st.dataframe(filtered[[
                col for col in ["Student Doctor's Name", "SBM Name", "RBM Name", "Potential"]
                if col in filtered.columns
            ]])

    # TABLES FOR POTENTIAL
    st.subheader("💎 Doctors by Potential")
    if "Potential" in df.columns:
        for pot in ["High", "Medium", "Low"]:
            st.markdown(f"**{pot} Potential Doctors:**")
            filtered = df[df["Potential"] == pot]
            st.dataframe(filtered[[
                col for col in ["Student Doctor's Name", "SBM Name", "RBM Name", "Prescriber Type"]
                if col in filtered.columns
            ]])

    # DOWNLOAD OPTION
    st.markdown("---")
    st.markdown(download_button(df), unsafe_allow_html=True)
