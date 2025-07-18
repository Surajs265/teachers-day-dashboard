import streamlit as st
import pandas as pd
import plotly.express as px

# Load data
st.set_page_config(layout="wide")
st.title("📊 Teachers' Day Campaign Dashboard")

uploaded_file = st.file_uploader("Upload Final Response Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Cleaning and renaming
    df.columns = df.columns.str.strip()
    df['Prescriber Type'] = df['Prescriber Type'].astype(str).str.strip().str.lower()
    df['Prescriber Type'] = df['Prescriber Type'].replace({
        'regular prescriber': 'Regular', 'occasional prescriber': 'Occasional',
        'non prescriber': 'Non-Prescriber', 'rp': 'Regular', 'op': 'Occasional',
        'np': 'Non-Prescriber'
    })

    df['Potential'] = df['Potential'].astype(str).str.strip().str.lower()
    df['Potential'] = df['Potential'].replace({
        'high': 'High', 'medium': 'Medium', 'low': 'Low'
    })

    # Sidebar Filters
    with st.sidebar:
        st.header("🔍 Filters")
        selected_state = st.multiselect("Select State", df['Student Doctor\'s State'].dropna().unique())
        selected_rbm = st.multiselect("Select RBM/ZBM", df['RBM/ZBM Name'].dropna().unique())
        selected_sbm = st.multiselect("Select SBM", df['User Name'].dropna().unique())

    filtered_df = df.copy()
    if selected_state:
        filtered_df = filtered_df[filtered_df['Student Doctor\'s State'].isin(selected_state)]
    if selected_rbm:
        filtered_df = filtered_df[filtered_df['RBM/ZBM Name'].isin(selected_rbm)]
    if selected_sbm:
        filtered_df = filtered_df[filtered_df['User Name'].isin(selected_sbm)]

    # KPIs
    total_entries = len(filtered_df)
    unique_doctors = filtered_df['Student Doctor\'s Name'].nunique()
    unique_sbm = filtered_df['User Name'].nunique()

    col1, col2, col3 = st.columns(3)
    col1.metric("📥 Total Entries", total_entries)
    col2.metric("👨‍⚕️ Unique Doctors", unique_doctors)
    col3.metric("🧑‍💼 Unique SBMs", unique_sbm)

    # Pie Chart - Prescriber Type
    st.subheader("🥧 Prescriber Type Distribution")
    pie_data = filtered_df['Prescriber Type'].value_counts().reset_index()
    pie_data.columns = ['Prescriber Type', 'Count']
    fig_pie = px.pie(pie_data, names='Prescriber Type', values='Count', title='Prescriber Type Split')
    st.plotly_chart(fig_pie, use_container_width=True)

    # Doctor List
    st.subheader("📋 Doctor List by Prescriber Type & Potential")
    for ptype in ['Regular', 'Occasional', 'Non-Prescriber']:
        for pot in ['High', 'Medium', 'Low']:
            group = filtered_df[(filtered_df['Prescriber Type'] == ptype) & (filtered_df['Potential'] == pot)]
            if not group.empty:
                with st.expander(f"{ptype} - {pot} Potential ({len(group)} doctors)"):
                    st.dataframe(group[['Student Doctor\'s Name', 'Student Doctor\'s City', 'RBM/ZBM Name']].drop_duplicates())

    # Heatmap - SBM vs City
    st.subheader("🌆 Heatmap: Entries by SBM & City")
    heat_data = filtered_df.groupby(['User Name', 'Student Doctor\'s City']).size().reset_index(name='Counts')
    heat_pivot = heat_data.pivot(index='User Name', columns='Student Doctor\'s City', values='Counts').fillna(0)
    st.dataframe(heat_pivot.style.background_gradient(cmap='Blues'), height=400)

    # Stacked Bar - SBM vs Prescriber Type
    st.subheader("📊 Prescriber Type by SBM")
    bar_data = filtered_df.groupby(['User Name', 'Prescriber Type']).size().reset_index(name='Counts')
    fig_bar = px.bar(bar_data, x='User Name', y='Counts', color='Prescriber Type', title='Prescriber Type by SBM', barmode='stack')
    st.plotly_chart(fig_bar, use_container_width=True)

    # RBM Summary
    st.subheader("📋 Per-RBM Summary")
    rbm_summary = filtered_df.groupby('RBM/ZBM Name').agg({
        'Student Doctor\'s Name': pd.Series.nunique,
        'User Name': pd.Series.nunique
    }).reset_index().rename(columns={
        'Student Doctor\'s Name': 'Unique Doctors',
        'User Name': 'SBM Count'
    })
    st.dataframe(rbm_summary)

    # KPI Target Chart
    st.subheader("🎯 RBM Performance Against Target")
    target = st.slider("Set Doctor Target per RBM", 50, 200, 100)
    rbm_summary['% Achieved'] = (rbm_summary['Unique Doctors'] / target * 100).round(1)
    fig_target = px.bar(rbm_summary, x='RBM/ZBM Name', y='% Achieved', color='% Achieved',
                        color_continuous_scale='RdYlGn', range_y=[0, 150],
                        title='RBM Doctor Count Achievement (%)')
    st.plotly_chart(fig_target, use_container_width=True)

else:
    st.info("📥 Please upload your Teachers' Day final response Excel file to begin.")
