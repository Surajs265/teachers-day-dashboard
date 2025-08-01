import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from thefuzz import process

# Page settings
st.set_page_config(layout="wide")
st.markdown("""
    <style>
    .stApp {
        background-color: #f4f6f9;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .css-1d391kg {
        padding: 1rem;
        border-radius: 1rem;
        background-color: white;
        box-shadow: 0 0 10px rgba(0,0,0,0.08);
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Teachers' Day Campaign Dashboard")

# Upload
uploaded_file = st.file_uploader("📁 Upload Teachers' Day Excel/CSV File", type=["xlsx", "csv"])

if uploaded_file:
    with st.spinner("Processing uploaded file... please wait ⏳"):
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        df.columns = df.columns.str.strip()
        df.dropna(subset=["Student Doctor's Name", "Teacher's Doctor's Name"], inplace=True)

        unique_sbms = df['User Name'].unique()
        standard_sbms = list(set(unique_sbms))[:75]

        def match_sbm(name):
            match, score = process.extractOne(name, standard_sbms)
            return match if score > 95 else name

        df['User Name'] = df['User Name'].apply(match_sbm)

        if 'Entry Date' in df.columns:
            df['Entry Date'] = pd.to_datetime(df['Entry Date'], errors='coerce')

        st.sidebar.header("🔍 Filters")
        sbm_filter = st.sidebar.multiselect("Filter by SBM", sorted(df['User Name'].unique()))
        state_filter = st.sidebar.multiselect("Filter by State", sorted(df["Student Doctor's State"].dropna().unique()))
        if 'Entry Date' in df.columns:
            min_date, max_date = df['Entry Date'].min(), df['Entry Date'].max()
            date_range = st.sidebar.date_input("Filter by Date", [min_date, max_date])
        else:
            date_range = None

        if sbm_filter:
            df = df[df['User Name'].isin(sbm_filter)]
        if state_filter:
            df = df[df["Student Doctor's State"].isin(state_filter)]
        if date_range and len(date_range) == 2:
            df = df[(df['Entry Date'] >= pd.to_datetime(date_range[0])) & (df['Entry Date'] <= pd.to_datetime(date_range[1]))]

        total_entries = len(df)
        unique_students = df["Student Doctor's Name"].nunique()
        unique_teachers = df["Teacher's Doctor's Name"].nunique()
        duplicate_teacher_mentions = total_entries - unique_teachers
        sbm_count = df['User Name'].nunique()
        avg_responses_per_sbm = round(total_entries / sbm_count, 2)

        assigned_per_sbm = 100
        execution_df = df.groupby('User Name')["Student Doctor's Name"].nunique().reset_index()
        execution_df.columns = ['User Name', 'Unique Student Doctors']
        execution_df['Execution %'] = round((execution_df['Unique Student Doctors'] / assigned_per_sbm) * 100, 2)
        avg_execution = round(execution_df['Execution %'].mean(), 2)

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📈 Summary",
            "👤 SBM Execution",
            "👨‍🏫 Teacher Analysis",
            "📋 Duplicates",
            "🌍 Advanced Visuals",
            "📌 RBM Summary"
        ])

        with tab1:
            st.header("📌 Overall Summary")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Responses", total_entries)
            col2.metric("Unique Students", unique_students)
            col3.metric("Unique Teachers", unique_teachers)

            col4, col5, col6 = st.columns(3)
            col4.metric("Duplicate Mentions", duplicate_teacher_mentions)
            col5.metric("SBMs Count", sbm_count)
            col6.metric("Avg. Responses/SBM", avg_responses_per_sbm)

            st.metric("Avg Execution %", f"{avg_execution}%")

            st.subheader("📊 Charts")

            with st.expander("🟢 Pie Chart: SBM-wise Contribution"):
                sbm_pie = df['User Name'].value_counts().reset_index()
                sbm_pie.columns = ['User Name', 'Responses']
                fig_pie = px.pie(sbm_pie, names='User Name', values='Responses', hole=0.4,
                                 color_discrete_sequence=px.colors.sequential.Tealgrn)
                fig_pie.update_layout(margin=dict(t=30, b=10), font=dict(size=14), paper_bgcolor='#f4f6f9')
                st.plotly_chart(fig_pie, use_container_width=True)

            with st.expander("📈 Line Chart: Daily Trend"):
                if 'Entry Date' in df.columns:
                    trend = df.groupby(df['Entry Date'].dt.date).size().reset_index(name='Responses')
                    fig_line = px.line(trend, x='Entry Date', y='Responses', markers=True,
                                       color_discrete_sequence=['#117864'])
                    fig_line.update_traces(mode='lines+markers', hovertemplate='Date: %{x}<br>Responses: %{y}')
                    fig_line.update_layout(margin=dict(t=30, b=10), paper_bgcolor='#f4f6f9')
                    st.plotly_chart(fig_line, use_container_width=True)

            with st.expander("🏙️ Bar Chart: Top Cities"):
                if "Student Doctor's City" in df.columns:
                    city_chart = df["Student Doctor's City"].value_counts().reset_index().head(10)
                    city_chart.columns = ['City', 'Responses']
                    fig_city = px.bar(city_chart, x='City', y='Responses', color='Responses',
                                      color_continuous_scale='Tealgrn')
                    fig_city.update_traces(text=city_chart['Responses'], textposition='outside')
                    fig_city.update_layout(margin=dict(t=30, b=10), paper_bgcolor='#f4f6f9')
                    st.plotly_chart(fig_city, use_container_width=True)

        with tab2:
            st.header("🔢 SBM Execution Summary")
            execution_df['Rank'] = execution_df['Execution %'].rank(ascending=False).astype(int)
            st.dataframe(execution_df.sort_values("Execution %", ascending=False), use_container_width=True, height=400)

            st.subheader("⚠️ Low Performing SBMs (<60%)")
            st.dataframe(execution_df[execution_df['Execution %'] < 60], use_container_width=True)

            def to_excel(df):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='SBM Summary')
                return output.getvalue()

            excel = to_excel(execution_df)
            st.download_button("📥 Download Summary", data=excel, file_name="sbm_summary.xlsx")

        with tab3:
            st.header("👨‍🏫 Top Teachers")
            teacher_counts = df["Teacher's Doctor's Name"].value_counts().reset_index()
            teacher_counts.columns = ['Teacher Name', 'Mentions']
            st.dataframe(teacher_counts.head(10), use_container_width=True)
            fig = px.bar(teacher_counts.head(10), x='Mentions', y='Teacher Name', orientation='h',
                         color='Mentions', color_continuous_scale='Tealgrn')
            fig.update_layout(paper_bgcolor='#f4f6f9')
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            st.header("📋 Duplicate Teacher Doctors")
            multi_teachers = df[df.duplicated("Teacher's Doctor's Name", keep=False)]
            st.dataframe(multi_teachers[["Teacher's Doctor's Name", "Student Doctor's Name", "Student Doctor's City"]],
                         use_container_width=True)

        with tab5:
            st.header("📊 Advanced Visuals")

            st.subheader("🔥 Heatmap: SBM vs City")
            if "Student Doctor's City" in df.columns:
                heat_df = df.pivot_table(index='User Name', columns="Student Doctor's City",
                                         values="Student Doctor's Name", aggfunc='count', fill_value=0)
                fig_heat = px.imshow(heat_df, aspect='auto', color_continuous_scale='YlGnBu')
                fig_heat.update_layout(paper_bgcolor='#f4f6f9')
                st.plotly_chart(fig_heat, use_container_width=True)

            st.subheader("📊 Stacked Bar: SBM & City")
            if "Student Doctor's City" in df.columns:
                stacked_df = df.groupby(['User Name', "Student Doctor's City"]).size().reset_index(name='Count')
                fig_stacked = px.bar(stacked_df, x='User Name', y='Count', color="Student Doctor's City")
                fig_stacked.update_layout(paper_bgcolor='#f4f6f9')
                st.plotly_chart(fig_stacked, use_container_width=True)

        with tab6:
            st.header("📌 RBM Summary & KPI Target (100 Doctors)")
            if "HQ Code" in df.columns:
                rbm_df = df.groupby('HQ Code')["Student Doctor's Name"].nunique().reset_index()
                rbm_df.columns = ['RBM', 'Unique Student Doctors']
                rbm_df['Execution %'] = round((rbm_df['Unique Student Doctors'] / assigned_per_sbm) * 100, 2)
                st.dataframe(rbm_df.sort_values('Execution %', ascending=False), use_container_width=True)

                fig_rbm = px.bar(rbm_df, x='RBM', y='Execution %', color='Execution %',
                                 title='RBM-wise Execution %', color_continuous_scale='tealgrn')
                fig_rbm.update_layout(paper_bgcolor='#f4f6f9')
                st.plotly_chart(fig_rbm, use_container_width=True)
            else:
                st.warning("❗ 'HQ Code' column not found for RBM analysis.")
else:
    st.info("Please upload a Teachers' Day data file to get started.")
