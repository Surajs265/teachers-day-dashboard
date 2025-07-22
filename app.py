import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from thefuzz import process

st.set_page_config(layout="wide")
st.title("📊 Teachers' Day Campaign Dashboard")

# Upload main Teachers' Day file
uploaded_file = st.file_uploader("📁 Upload Teachers' Day Excel/CSV File", type=["xlsx", "csv"])

# Upload SBM Master List (Optional)
sbm_master_file = st.sidebar.file_uploader("📌 Upload Master SBM List (Optional)", type=["csv"])

if uploaded_file:
    with st.spinner("Processing uploaded file... please wait ⏳"):

        # Load main data
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Clean & normalize
        df.columns = df.columns.str.strip()
        df.dropna(subset=["Student Doctor's Name", "Teacher's Doctor's Name"], inplace=True)

        # Load SBM master (if provided)
        if sbm_master_file:
            sbm_master = pd.read_csv(sbm_master_file)
            standard_sbms = sbm_master['SBM'].dropna().unique().tolist()
        else:
            standard_sbms = df['User Name'].dropna().unique().tolist()

        # Fuzzy match SBM names
        def match_sbm(name):
            match, score = process.extractOne(name, standard_sbms)
            return match if score > 95 else name

        df['User Name'] = df['User Name'].apply(match_sbm)

        # Date column
        if 'Entry Date' in df.columns:
            df['Entry Date'] = pd.to_datetime(df['Entry Date'], errors='coerce')

        # Sidebar Filters
        st.sidebar.header("🔍 Filters")
        sbm_filter = st.sidebar.multiselect("Filter by SBM", sorted(df['User Name'].unique()))
        state_filter = st.sidebar.multiselect("Filter by State", sorted(df["Student Doctor's State"].dropna().unique()))
        if 'Entry Date' in df.columns:
            min_date, max_date = df['Entry Date'].min(), df['Entry Date'].max()
            date_range = st.sidebar.date_input("Filter by Date", [min_date, max_date])
        else:
            date_range = None

        # Apply Filters
        if sbm_filter:
            df = df[df['User Name'].isin(sbm_filter)]
        if state_filter:
            df = df[df["Student Doctor's State"].isin(state_filter)]
        if date_range and len(date_range) == 2:
            df = df[(df['Entry Date'] >= pd.to_datetime(date_range[0])) & (df['Entry Date'] <= pd.to_datetime(date_range[1]))]

        # Metrics
        total_entries = len(df)
        unique_students = df["Student Doctor's Name"].nunique()
        unique_teachers = df["Teacher's Doctor's Name"].nunique()
        duplicate_teacher_mentions = total_entries - unique_teachers
        sbm_count = df['User Name'].nunique()
        avg_responses_per_sbm = round(total_entries / sbm_count, 2)

        # SBM Execution
        assigned_per_sbm = 100
        execution_df = df.groupby('User Name')["Student Doctor's Name"].nunique().reset_index()
        execution_df.columns = ['User Name', 'Unique Student Doctors']
        execution_df['Execution %'] = round((execution_df['Unique Student Doctors'] / assigned_per_sbm) * 100, 2)
        avg_execution = round(execution_df['Execution %'].mean(), 2)

        # Tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📈 Summary", "👤 SBM Execution", "👨‍🏫 Teacher Analysis",
            "📋 Duplicates", "🌍 Advanced Visuals", "📌 RBM Summary"
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
                fig_pie = px.pie(sbm_pie, names='User Name', values='Responses', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

            with st.expander("📈 Line Chart: Daily Trend"):
                if 'Entry Date' in df.columns:
                    trend = df.groupby(df['Entry Date'].dt.date).size().reset_index(name='Responses')
                    fig_line = px.line(trend, x='Entry Date', y='Responses', markers=True)
                    st.plotly_chart(fig_line, use_container_width=True)

            with st.expander("🏙️ Bar Chart: Top Cities"):
                if "Student Doctor's City" in df.columns:
                    city_chart = df["Student Doctor's City"].value_counts().reset_index().head(10)
                    city_chart.columns = ['City', 'Responses']
                    fig_city = px.bar(city_chart, x='City', y='Responses', color='Responses')
                    st.plotly_chart(fig_city, use_container_width=True)

        with tab2:
            st.header("🔢 SBM Execution Summary")
            execution_df['Rank'] = execution_df['Execution %'].rank(ascending=False).astype(int)
            st.dataframe(execution_df.sort_values("Execution %", ascending=False))

            st.subheader("⚠️ Low Performing SBMs (<40%)")
            st.dataframe(execution_df[execution_df['Execution %'] < 40])

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
            st.dataframe(teacher_counts.head(10))
            fig = px.bar(teacher_counts.head(10), x='Mentions', y='Teacher Name', orientation='h')
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            st.header("📋 Duplicate Teacher Doctors")
            multi_teachers = df[df.duplicated("Teacher's Doctor's Name", keep=False)]
            st.dataframe(multi_teachers[["Teacher's Doctor's Name", "Student Doctor's Name", "Student Doctor's City"]])

        with tab5:
            st.header("📊 Advanced Visuals")

            st.subheader("🔥 Heatmap: SBM vs City")
            if "Student Doctor's City" in df.columns:
                heat_df = df.pivot_table(index='User Name', columns="Student Doctor's City", values="Student Doctor's Name", aggfunc='count', fill_value=0)
                fig_heat = px.imshow(heat_df, aspect='auto', color_continuous_scale='YlGnBu')
                st.plotly_chart(fig_heat, use_container_width=True)

            st.subheader("📊 Stacked Bar: SBM & City")
            if "Student Doctor's City" in df.columns:
                stacked_df = df.groupby(['User Name', "Student Doctor's City"]).size().reset_index(name='Count')
                fig
