import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from thefuzz import process

st.set_page_config(page_title="Teachers' Day Dashboard", layout="wide")

st.title("🎓 Teachers' Day Campaign Dashboard")

# Upload main data
uploaded_file = st.sidebar.file_uploader("📂 Upload Teachers' Day Data (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip()
    df["User Name"] = df["User Name"].astype(str).str.strip()

    # --- Upload Master SBM List ---
    st.sidebar.markdown("### 🧩 Master SBM Matching (Optional)")
    sbm_master_file = st.sidebar.file_uploader("📌 Upload SBM Master CSV", type=["csv"])
    
    if sbm_master_file:
        sbm_master = pd.read_csv(sbm_master_file)
        st.sidebar.write("📄 Columns:", sbm_master.columns.tolist())
        selected_col = st.sidebar.selectbox("Select SBM Column", sbm_master.columns)
        try:
            standard_sbms = sbm_master[selected_col].dropna().astype(str).str.strip().unique().tolist()
        except:
            st.error("❌ Error reading selected SBM column.")
            st.stop()
    else:
        standard_sbms = df["User Name"].dropna().astype(str).str.strip().unique().tolist()

    # --- SBM Fuzzy Matching ---
    def match_sbm(name):
        match, score = process.extractOne(name, standard_sbms)
        return match if score >= 95 else name

    df["User Name"] = df["User Name"].apply(match_sbm)

    # --- Metrics ---
    total_responses = df.shape[0]
    unique_students = df["Student Doctor's Name"].nunique()
    unique_teachers = df["Teacher's Name"].nunique()

    col1, col2, col3 = st.columns(3)
    col1.metric("📬 Total Responses", total_responses)
    col2.metric("🧑‍⚕️ Unique Student Doctors", unique_students)
    col3.metric("👨‍🏫 Unique Teachers", unique_teachers)

    # --- Execution by SBM ---
    st.markdown("### 📊 Execution by SBM")
    sbm_exec = df.groupby("User Name")["Student Doctor's Name"].nunique().reset_index()
    sbm_exec.columns = ["SBM", "Unique Student Count"]
    sbm_exec["Execution %"] = (sbm_exec["Unique Student Count"] / 100 * 100).round(2)

    st.dataframe(sbm_exec.sort_values("Execution %", ascending=False), use_container_width=True)

    # --- Top Teachers ---
    st.markdown("### 🏅 Top 10 Teachers (By Number of Mentions)")
    top_teachers = df["Teacher's Name"].value_counts().head(10).reset_index()
    top_teachers.columns = ["Teacher", "Mentions"]
    fig1 = px.bar(top_teachers, x="Mentions", y="Teacher", orientation="h", title="Top 10 Teachers", text="Mentions")
    st.plotly_chart(fig1, use_container_width=True)

    # --- Top Student Doctors ---
    st.markdown("### 👨‍⚕️ Top 10 Student Doctors (By Number of Entries)")
    top_students = df["Student Doctor's Name"].value_counts().head(10).reset_index()
    top_students.columns = ["Student Doctor", "Entries"]
    fig2 = px.bar(top_students, x="Entries", y="Student Doctor", orientation="h", title="Top 10 Student Doctors", text="Entries")
    st.plotly_chart(fig2, use_container_width=True)

    # --- Filter by SBM ---
    st.markdown("### 🗂 SBM-wise Breakdown")
    selected_sbm = st.selectbox("Select SBM to View", sbm_exec["SBM"].sort_values())
    sbm_data = df[df["User Name"] == selected_sbm]
    st.write(f"📄 Showing {sbm_data.shape[0]} entries for **{selected_sbm}**:")
    st.dataframe(sbm_data, use_container_width=True)

    # --- Download Execution Data ---
    def to_excel(df):
        return df.to_csv(index=False).encode("utf-8")

    st.sidebar.download_button("📥 Download SBM Execution CSV", data=to_excel(sbm_exec), file_name="sbm_execution.csv", mime="text/csv")

else:
    st.warning("📤 Please upload your Teachers' Day data file to get started.")
