import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from rapidfuzz import process

st.set_page_config(layout="wide")
st.title("📊 Teachers' Day Campaign Dashboard")

uploaded_file = st.file_uploader("📁 Upload Teachers' Day Excel/CSV File", type=["xlsx", "csv"])

@st.cache_data(show_spinner=False)
def load_data(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file, engine="openpyxl")

@st.cache_data(show_spinner=False)
def preprocess_data(df):
    df.columns = df.columns.str.strip()
    df.dropna(subset=["Student Doctor's Name", "Teacher's Doctor's Name"], inplace=True)

    # Fuzzy match SBM names
    unique_sbms = df['User Name'].unique()
    standard_sbms = list(set(unique_sbms))[:75]
    def match_sbm(name):
        match, score, _ = process.extractOne(name, standard_sbms)
        return match if score > 95 else name
    df['User Name'] = df['User Name'].apply(match_sbm)

    if 'Entry Date' in df.columns:
        df['Entry Date'] = pd.to_datetime(df['Entry Date'], errors='coerce')

    return df

if uploaded_file:
    with st.spinner("Processing uploaded file... please wait ⏳"):
        df = load_data(uploaded_file)
        df = preprocess_data(df)

        # Sidebar Filters
        st.sidebar.header("🔍 Filters")

        sbm_filter = st.sidebar.multiselect(
            "Filter by SBM", sorted(df['User Name'].dropna().unique())
        )

        # ✅ FIX: Use .get() to safely access column
        state_filter = st.sidebar.multiselect(
            "Filter by State",
            sorted(df.get("Student Doctor's State", pd.Series(dtype='str')).dropna().unique())
        )

        rbm_filter = st.sidebar.multiselect(
            "Filter by RBM", sorted(df.get('HQ Code', pd.Series(dtype='str')).dropna().unique())
        )

        if 'Entry Date' in df.columns:
            min_date, max_date = df['Entry Date'].min(), df['Entry Date'].max()
            date_range = st.sidebar.date_input("Filter by Date", [min_date, max_date])
        else:
            date_range = None

        # Apply Filters
        if sbm_filter:
            df = df[df['User Name'].isin(sbm_filter)]
        if state_filter and "Student Doctor's State" in df.columns:
            df = df[df["Student Doctor's State"].isin(state_filter)]
        if rbm_filter and "HQ Code" in df.columns:
            df = df[df['HQ Code'].isin(rbm_filter)]
        if date_range and len(date_range) == 2:
            df = df[(df['Entry Date'] >= pd.to_datetime(date_range[0])) & (df['Entry Date'] <= pd.to_datetime(date_range[1]))]

        # Metrics
        total_entries = len(df)
        unique_students = df["Student Doctor's Name"].nunique()
        unique_teachers = df["Teacher's Doctor's Name"].nunique()
        duplicate_teacher_mentions = total_entries - unique_teachers
        sbm_count = df['User Name'].nunique()
        avg_responses_per_sbm = round(total_entries / sbm_count, 2) if sbm_count else 0

        assigned_per_sbm = 100
        execution_df = df.groupby('User Name')["Student Doctor's Name"].nunique().reset_index()
        execution_df.columns = ['User Name', 'Unique Student Doctors']
        execution_df['Execution %'] = round((execution_df['Unique Student Doctors'] / assigned_per_sbm) * 100, 2)
        avg_execution = round(execution_df['Execution %'].mean(), 2)

        sbm_rbm_map = df.groupby('User Name')['HQ Code'].agg(lambda x: x.dropna().unique()[0] if len(x.dropna().unique()) > 0 else 'Unknown').to_dict()
        execution_df['RBM'] = execution_df['User Name'].map(sbm_rbm_map)

        # Tabs
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📈 Summary",
            "👤 SBM Execution",
            "👨‍🏫 Teacher Analysis",
            "📋 Duplicates",
            "🌍 Advanced Visuals",
            "📌 RBM Summary",
            "🔎 RBM-to-SBM Drilldown"
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
                    trend.columns = ['Entry Date', 'Responses']
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

            st.subheader("⚠️ Low Performing SBMs (<60%)")
            st.dataframe(execution_df[execution_df['Execution %'] < 60])

            def to_excel(df):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='SBM Summary')
                output.seek(0)
                return output.read()

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
                fig_stacked = px.bar(stacked_df, x='User Name', y='Count', color="Student Doctor's City")
                st.plotly_chart(fig_stacked, use_container_width=True)

        with tab6:
            st.header("📌 RBM Summary & KPI Target (100 Doctors)")

            if 'RBM' in execution_df.columns:
                rbm_summary = execution_df.groupby('RBM')['Unique Student Doctors'].sum().reset_index()
                rbm_summary['Execution %'] = round((rbm_summary['Unique Student Doctors'] / (assigned_per_sbm * sbm_count)) * 100, 2)
                st.dataframe(rbm_summary.sort_values('Execution %', ascending=False))

                fig_rbm = px.bar(rbm_summary, x='RBM', y='Execution %', color='Execution %',
                                 title='RBM-wise Execution % (Aggregated from SBM)', color_continuous_scale='tealgrn')
                st.plotly_chart(fig_rbm, use_container_width=True)
            else:
                st.warning("❗ RBM mapping not found for RBM analysis.")

        with tab7:
            st.header("🔎 RBM-to-SBM Drilldown")
            selected_rbm = st.selectbox("Select RBM", sorted(execution_df['RBM'].dropna().unique()))
            filtered_sbms = execution_df[execution_df['RBM'] == selected_rbm]
            st.subheader(f"SBM Performance under RBM: {selected_rbm}")
            st.dataframe(filtered_sbms.sort_values('Execution %', ascending=False))

else:
    st.info("Please upload a Teachers' Day data file to get started.")
