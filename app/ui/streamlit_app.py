import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.analytics.anomaly_engine import anomaly_detector
from app.analytics.kpi_engine import kpi_engine
from app.analytics.semantic_engine import semantic_engine
from app.database.db_manager import db_manager
from app.ingestion.pipeline import ingestion_pipeline
from app.nlp.llm_client import llm_client
from app.nlp.query_service import query_service

# Page Configuration
st.set_page_config(
    page_title="Support Ticket Intelligence AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .diag-box {
        background-color: #F1F5F9;
        border-left: 4px solid #3B82F6;
        padding: 14px;
        border-radius: 4px;
        margin-top: 10px;
    }
    .playbook-item {
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        padding: 8px 12px;
        border-radius: 6px;
        margin-bottom: 6px;
        font-size: 0.92rem;
    }
</style>
""", unsafe_allow_html=True)

# Ensure Database is seeded
@st.cache_resource
def init_app_state():
    db_manager.init_database()
    if db_manager.get_ticket_count() == 0:
        ingestion_pipeline.run()
    semantic_engine.ensure_index()
    return True

init_app_state()

# Sidebar Navigation & Settings
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=150&auto=format&fit=crop&q=80", width=80)
    st.title("Operations AI")
    st.caption("Enterprise Support Intelligence")
    st.divider()

    st.subheader("System Status")
    total_count = db_manager.get_ticket_count()
    st.write(f"📊 **Database**: {total_count} tickets")
    active_provider = llm_client.get_active_provider_name()
    st.write(f"🧠 **AI Engine**: {active_provider}")
    st.divider()

    st.subheader("Quick Actions")
    if st.button("🔄 Refresh Data & Cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if st.button("📥 Force Re-ingest CSV", use_container_width=True):
        summary = ingestion_pipeline.run(force_reload=True)
        st.success(f"Re-ingested {summary['records_inserted']} rows!")
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Built for DOTMappers AI Engineer Assessment.")

# Top Header
st.markdown('<div class="main-header">🛡️ Support Ticket Intelligence Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Automated operational analytics, AI-powered Text-to-SQL querying, semantic issue discovery, and statistical anomaly detection.</div>', unsafe_allow_html=True)

# Load Top KPIs
kpis = kpi_engine.get_executive_summary()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Tickets", kpis["total_tickets"])
with col2:
    st.metric("Active Backlog", f"{kpis['open_tickets'] + kpis['escalated_tickets']} tickets", delta=f"{kpis['open_tickets']} Open", delta_color="inverse")
with col3:
    st.metric("Resolution Rate", f"{kpis['resolution_rate_pct']}%")
with col4:
    st.metric("Avg Resolution Time", f"{kpis['avg_resolution_time_hrs']} hrs")
with col5:
    st.metric("Customer CSAT", f"{kpis['avg_customer_rating']} / 5.0")

st.write("")

# Navigation Tabs (5 Tabs: Added Semantic Discovery)
tab_chat, tab_anomalies, tab_semantic, tab_analytics, tab_explorer = st.tabs([
    "💬 AI Assistant (Hybrid Text-to-SQL + Semantic)",
    "🚨 Anomaly Center & AI Diagnostician",
    "🧠 Semantic Discovery & Issue Clusters",
    "📈 Executive Dashboard",
    "🔍 Ticket Data Explorer"
])

# -------------------------------------------------------------
# TAB 1: Conversational AI Assistant
# -------------------------------------------------------------
with tab_chat:
    st.markdown("### Ask Natural Language Questions")
    st.write("Supports both **Structured Text-to-SQL Analytics** and **Qualitative Semantic Search** over support tickets.")

    st.markdown("**Sample Assessment Queries (Click to Run):**")
    chip_col1, chip_col2, chip_col3 = st.columns(3)
    chip_col4, chip_col5, chip_col6 = st.columns(3)

    sample_prompt = None
    with chip_col1:
        if st.button("📌 How many tickets are currently open?", use_container_width=True):
            sample_prompt = "How many tickets are currently open?"
    with chip_col2:
        if st.button("📌 Which agent resolved the most tickets this month?", use_container_width=True):
            sample_prompt = "Which agent resolved the most tickets this month?"
    with chip_col3:
        if st.button("📌 Show Critical tickets not resolved in 12 hrs", use_container_width=True):
            sample_prompt = "Show me all Critical tickets not resolved within 12 hours."
    with chip_col4:
        if st.button("📌 Avg CSAT rating for Technical tickets?", use_container_width=True):
            sample_prompt = "What is the average customer rating for Technical category tickets?"
    with chip_col5:
        if st.button("📌 Are there anomalies in resolution times?", use_container_width=True):
            sample_prompt = "Are there any anomalies in resolution times this week?"
    with chip_col6:
        if st.button("📌 Find tickets related to login failure", use_container_width=True):
            sample_prompt = "Find tickets related to login failure after update"

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_query = st.chat_input("Ask a quantitative or semantic question (e.g. 'What are the common issues?' or 'Average response time?')...")
    active_query = sample_prompt or user_query

    if active_query:
        with st.spinner("Processing query and synthesizing intelligence..."):
            response = query_service.process_query(active_query)
            st.session_state.chat_history.append((active_query, response))

    # Render History
    for q, res in reversed(st.session_state.chat_history):
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            st.markdown(res["answer"])

            with st.expander(f"🔍 Technical Inspection ({res['execution_time_ms']} ms | {res['provider']})"):
                st.code(res["sql"], language="sql")
                if res.get("error"):
                    st.error(f"Error: {res['error']}")

            if res.get("data") and len(res["data"]) > 0:
                df_res = pd.DataFrame(res["data"])
                if res["chart_type"] == "metric_card" and len(df_res.columns) == 1:
                    col_name = df_res.columns[0]
                    st.metric(label=col_name.replace("_", " ").title(), value=df_res.iloc[0, 0])
                elif res["chart_type"] == "bar_chart" and len(df_res.columns) >= 2:
                    x_col = df_res.columns[0]
                    y_col = df_res.columns[1]
                    fig = px.bar(df_res, x=x_col, y=y_col, title=f"{y_col} by {x_col}", color=x_col)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.dataframe(df_res, use_container_width=True)
        st.divider()

# -------------------------------------------------------------
# TAB 2: Anomaly Center & AI Diagnostician
# -------------------------------------------------------------
with tab_anomalies:
    st.markdown("### 🚨 Anomaly Center & AI Root-Cause Diagnostician")
    st.write("Identifies SLA violations, stalled escalations, and resolution outliers with deep AI diagnosis.")

    all_anomalies = anomaly_detector.detect_all()
    anom_df = pd.DataFrame(all_anomalies)

    if not anom_df.empty:
        crit_count = sum(1 for a in all_anomalies if a["severity"] == "CRITICAL")
        warn_count = sum(1 for a in all_anomalies if a["severity"] in ("WARNING", "HIGH"))

        acol1, acol2, acol3, acol4 = st.columns(4)
        with acol1:
            st.metric("Total Flagged Anomalies", len(all_anomalies))
        with acol2:
            st.metric("Critical SLA Breaches", crit_count, delta="Action Required", delta_color="inverse")
        with acol3:
            st.metric("Statistical Outliers", warn_count)
        with acol4:
            st.metric("Methodology", "Operational Rules + Tukey IQR & Z-score")

        st.divider()

        # Visual Outlier Chart
        st.subheader("Resolution Time Outlier Distribution")
        tickets_rows = db_manager.execute_query("""
            SELECT ticket_id, created_at, category, priority, status, resolution_time_hrs
            FROM support_tickets WHERE status = 'Resolved' AND resolution_time_hrs IS NOT NULL;
        """)
        tdf = pd.DataFrame(tickets_rows)
        if not tdf.empty:
            tdf["created_at"] = pd.to_datetime(tdf["created_at"])
            q3 = tdf["resolution_time_hrs"].quantile(0.75)
            iqr = q3 - tdf["resolution_time_hrs"].quantile(0.25)
            cutoff = q3 + (1.5 * iqr)
            tdf["is_outlier"] = tdf["resolution_time_hrs"] > cutoff

            fig = px.scatter(
                tdf,
                x="created_at",
                y="resolution_time_hrs",
                color="is_outlier",
                color_discrete_map={True: "#EF4444", False: "#3B82F6"},
                hover_data=["ticket_id", "category", "priority", "resolution_time_hrs"],
                title=f"Resolution Times (IQR Cutoff: {cutoff:.1f} hrs)",
                labels={"created_at": "Ticket Date", "resolution_time_hrs": "Resolution Time (Hours)", "is_outlier": "Anomaly"}
            )
            fig.add_hline(y=cutoff, line_dash="dash", line_color="#EF4444", annotation_text=f"Anomaly Cutoff ({cutoff:.1f}h)")
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # AI Root-Cause Diagnostic Tool
        st.subheader("🤖 AI Root-Cause Diagnostician")
        st.write("Select any ticket to generate an immediate diagnostic breakdown, peer comparison, and mitigation playbook.")
        
        ticket_options = anom_df["ticket_id"].tolist()
        selected_ticket_id = st.selectbox("Select Ticket for Diagnosis:", ticket_options, index=0)
        
        if st.button(f"🔍 Run AI Diagnostic on {selected_ticket_id}", type="primary"):
            diag = semantic_engine.diagnose_anomaly(selected_ticket_id)
            with st.container():
                st.markdown(f"#### Diagnostic Report: `{selected_ticket_id}` ({diag['priority']} Priority | {diag['category']})")
                st.markdown(f'<div class="diag-box"><b>Findings:</b> {diag["diagnostic_summary"]}</div>', unsafe_allow_html=True)
                
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Ticket Resolution Time", f"{diag['resolution_time_hrs']} hrs" if diag['resolution_time_hrs'] else "Unresolved")
                with m2:
                    st.metric("Category Benchmark", f"{diag['category_benchmark_resol_hrs']} hrs")
                with m3:
                    st.metric("Agent Benchmark", f"{diag['agent_benchmark_resol_hrs']} hrs")

                st.markdown("**Actionable Remediation Playbook:**")
                for action in diag["action_playbook"]:
                    st.markdown(f'<div class="playbook-item">👉 {action}</div>', unsafe_allow_html=True)

                if diag.get("similar_tickets"):
                    st.write(f"**Similar Historical Incidents:** {', '.join(diag['similar_tickets'])}")

        st.divider()

        # Filtered Anomaly Table
        st.subheader("Flagged Tickets Directory")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            sev_filter = st.selectbox("Filter by Severity", ["All", "CRITICAL", "WARNING", "HIGH"])
        with f_col2:
            type_filter = st.selectbox("Filter by Anomaly Type", ["All"] + sorted(list(anom_df["anomaly_type"].unique())))

        filtered_anom = anom_df.copy()
        if sev_filter != "All":
            filtered_anom = filtered_anom[filtered_anom["severity"] == sev_filter]
        if type_filter != "All":
            filtered_anom = filtered_anom[filtered_anom["anomaly_type"] == type_filter]

        st.dataframe(
            filtered_anom[[
                "ticket_id", "severity", "anomaly_type", "priority", "category", 
                "metric_name", "metric_value", "threshold", "description", "recommendation"
            ]],
            use_container_width=True
        )

# -------------------------------------------------------------
# TAB 3: Semantic Discovery & Issue Clustering (NEW ENTERPRISE FEATURE)
# -------------------------------------------------------------
with tab_semantic:
    st.markdown("### 🧠 Semantic Discovery & Issue Clustering")
    st.write("Unsupervised NLP grouping of support tickets into core issue topics using TF-IDF and K-Means vector modeling.")

    # Topic Clusters
    st.subheader("Discovered Problem Themes")
    topics = semantic_engine.discover_topics(n_clusters=4)
    tcols = st.columns(len(topics))
    for idx, t in enumerate(topics):
        with tcols[idx]:
            st.markdown(f"**Topic {t['topic_id']} ({t['dominant_category']})**")
            st.metric(label="Tickets in Cluster", value=t["ticket_count"])
            st.write(f"⏱️ **Avg Resolution**: {t['avg_resolution_hrs']} hrs")
            st.write(f"⭐ **Avg CSAT**: {t['avg_csat']} / 5.0")
            st.caption(f"**Keywords**: {', '.join(t['keywords'])}")

    st.divider()

    # Semantic Vector Search
    st.subheader("Semantic Symptom Search")
    st.write("Find tickets semantically related to a description, even if exact keywords differ.")

    s_col1, s_col2 = st.columns([3, 1])
    with s_col1:
        search_query = st.text_input("Enter issue symptom (e.g. 'charged wrong amount on invoice', 'system logout timeout', 'data export'):")
    with s_col2:
        cat_filter = st.selectbox("Filter Category", ["All", "Billing", "Technical", "General"])

    if search_query:
        category_param = None if cat_filter == "All" else cat_filter
        matches = semantic_engine.search_similar(search_query, top_k=8, category=category_param)
        if matches:
            st.write(f"Found **{len(matches)}** semantically similar tickets:")
            m_df = pd.DataFrame(matches)
            st.dataframe(
                m_df[["ticket_id", "similarity_score", "category", "priority", "status", "issue_summary"]],
                use_container_width=True
            )
        else:
            st.info("No matching tickets found for that symptom.")

# -------------------------------------------------------------
# TAB 4: Executive Dashboard
# -------------------------------------------------------------
with tab_analytics:
    st.markdown("### Executive Overview & Support Metrics")

    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.subheader("Tickets by Category")
        cat_df = pd.DataFrame(kpis["categories"])
        if not cat_df.empty:
            fig_cat = px.pie(cat_df, names="category", values="count", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_cat, use_container_width=True)

    with dcol2:
        st.subheader("Tickets by Urgency Priority")
        prio_df = pd.DataFrame(kpis["priorities"])
        if not prio_df.empty:
            fig_prio = px.bar(prio_df, x="priority", y="count", color="priority", color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_prio, use_container_width=True)

    st.subheader("Support Agent Performance Leaderboard")
    agent_df = pd.DataFrame(kpis["agents"])
    if not agent_df.empty:
        st.dataframe(agent_df, use_container_width=True)

# -------------------------------------------------------------
# TAB 5: Ticket Data Explorer
# -------------------------------------------------------------
with tab_explorer:
    st.markdown("### Interactive Ticket Explorer")

    ecol1, ecol2, ecol3 = st.columns(3)
    with ecol1:
        sel_cat = st.multiselect("Category", ["Billing", "Technical", "General"], default=["Billing", "Technical", "General"])
    with ecol2:
        sel_prio = st.multiselect("Priority", ["Low", "Medium", "High", "Critical"], default=["Low", "Medium", "High", "Critical"])
    with ecol3:
        sel_stat = st.multiselect("Status", ["Open", "Resolved", "Escalated"], default=["Open", "Resolved", "Escalated"])

    search_kw = st.text_input("Search issue summary keywords:")

    all_tickets = db_manager.execute_query("""
        SELECT ticket_id, created_at, category, priority, status,
               response_time_hrs, resolution_time_hrs, agent_id,
               customer_rating, issue_summary
        FROM support_tickets ORDER BY created_at DESC;
    """)
    raw_df = pd.DataFrame(all_tickets)

    if not raw_df.empty:
        filtered_df = raw_df[
            (raw_df["category"].isin(sel_cat)) &
            (raw_df["priority"].isin(sel_prio)) &
            (raw_df["status"].isin(sel_stat))
        ]
        if search_kw:
            filtered_df = filtered_df[filtered_df["issue_summary"].str.contains(search_kw, case=False, na=False)]

        st.write(f"Displaying **{len(filtered_df)}** matching tickets:")
        st.dataframe(filtered_df, use_container_width=True)

        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv_data,
            file_name="support_tickets_filtered.csv",
            mime="text/csv"
        )
