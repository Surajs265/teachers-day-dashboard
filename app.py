import streamlit as st
import pandas as pd
import plotly.express as px
import base64
from io import BytesIO
from rapidfuzz import process

st.set_page_config(page_title="Teachers' Day Dashboard", layout="wide")
st.title("🎓 Teachers' Day Campaign Dashboard")
st.markdown("---")

@st.cache_data(show_spinner=False)
def load_excel(file):
    return pd.read_excel(file)

@st.cache_data(show_spinner=False)
def get_unique(df, col):
    return sorted(df.get(col, pd.Series(dtype='str')).dropna().unique().tolist())

@st.cache_data(show_spinner=False)
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

def get_download_link(df):
    val = to_excel(df)
    b64 = base64.b64encode(val).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="execution_data.xlsx">📥 Download Filtered Data</a>'

uploaded_file = st.file_uploader("📤 Upload your Teachers' Day data Excel file", type=["xlsx"])
if uploaded_file:
    df = load_excel(uploaded_file)
    df.columns = df.columns.str.strip()

    # Sidebar filters
    st.sidebar.header("🔎 Filters")
    state_list = get_unique(df, "Student Doctor's State")
    state_filter = st.sidebar.multiselect("Filter by State", state_list)

    sbm_list = get_unique(df, "SBM Name")
    sbm_filter = st.sidebar.multiselect("Filter by SBM", sbm_list)

    rbm_list = get_unique(df, "RBM Name")
    rbm_filter = st.sidebar.multiselect("Filter by RBM", rbm_list)

    # Apply filters
    filtered_df = df.copy()
    if state_filter:
        filtered_df = filtered_df[filtered_df["Student Doctor's State"].isin(state_filter)]
    if sbm_filter:
        filtered_df = filtered_df[filtered_df["SBM Name"].isin(sbm_filter)]
    if rbm_filter:
        filtered_df = filtered_df[filtered_df["RBM Name"].isin(rbm_filter)]

    st.subheader("📊 Overview Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Entries", len(filtered_df))
    col2.metric("Unique SBMs", filtered_df['SBM Name'].nunique())
    col3.metric("Unique RBMs", filtered_df['RBM Name'].nunique())

    st.markdown("---")
    st.subheader("🏆 SBM Performance")
    sbm_counts = filtered_df['SBM Name'].value_counts().reset_index()
    sbm_counts.columns = ['SBM Name', 'Entries']
    fig_sbm = px.bar(sbm_counts, x='SBM Name', y='Entries', text='Entries', height=400)
    st.plotly_chart(fig_sbm, use_container_width=True)

    st.subheader("🏢 RBM-wise Summary (Based on SBM Performance)")
    rbm_sbm_summary = filtered_df.groupby(['RBM Name', 'SBM Name']).size().reset_index(name='Entries')
    fig_rbm = px.sunburst(rbm_sbm_summary, path=['RBM Name', 'SBM Name'], values='Entries', height=500)
    st.plotly_chart(fig_rbm, use_container_width=True)

    st.subheader("🧠 Top & Bottom SBM Performers")
    top_sbm = sbm_counts.head(5)
    bottom_sbm = sbm_counts.tail(5)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🔝 Top 5 SBMs")
        st.dataframe(top_sbm)
    with col2:
        st.markdown("### 🔻 Bottom 5 SBMs")
        st.dataframe(bottom_sbm)

    st.markdown("---")
    st.subheader("📥 Download Filtered Execution Data")
    st.markdown(get_download_link(filtered_df), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🔍 SBM Name Matcher (Fuzzy Search)")
    name_to_match = st.text_input("Enter a SBM name to find closest matches:")
    if name_to_match:
        unique_names = df['SBM Name'].dropna().unique().tolist()
        matches = process.extract(name_to_match, unique_names, limit=5)
        for match in matches:
            st.write(f"✅ {match[0]} (Score: {match[1]})")
else:
    st.info("📂 Please upload an Excel file to begin.")
