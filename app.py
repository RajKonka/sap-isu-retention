"""
SAP IS-U Customer Retention Prediction System
Main Streamlit Application
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *

# ─── Page Config ─────────────────────────────────────────
st.set_page_config(
    page_title="SAP IS-U Customer Retention System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1a2e;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #0f3460;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .metric-card h3 { margin: 0; font-size: 2rem; }
    .metric-card p { margin: 0; opacity: 0.85; font-size: 0.9rem; }
    .risk-high { color: #e74c3c; font-weight: bold; }
    .risk-medium { color: #f39c12; font-weight: bold; }
    .risk-low { color: #27ae60; font-weight: bold; }
    .stChatMessage { border-radius: 12px; }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f3460 0%, #1a1a2e 100%);
    }
    div[data-testid="stSidebar"] .stMarkdown { color: white; }
    div[data-testid="stSidebar"] h1, div[data-testid="stSidebar"] h2,
    div[data-testid="stSidebar"] h3 { color: white; }
</style>
""", unsafe_allow_html=True)


# ─── Session State Initialization ────────────────────────
def init_session_state():
    if "data_generated" not in st.session_state:
        st.session_state.data_generated = False
    if "models_trained" not in st.session_state:
        st.session_state.models_trained = False
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "predictor" not in st.session_state:
        st.session_state.predictor = None
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = None
    if "merged_data" not in st.session_state:
        st.session_state.merged_data = None
    if "training_results" not in st.session_state:
        st.session_state.training_results = None


init_session_state()


# ─── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("# ⚡ SAP IS-U")
    st.markdown("### Customer Retention System")
    st.markdown("---")

    # API Key input
    api_key = st.text_input("Anthropic API Key (optional)", type="password",
                            help="Enter your API key to enable AI-powered chatbot")
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

    st.markdown("---")
    st.markdown("### Pipeline Steps")

    # Step 1: Generate Data
    if st.button("🔄 1. Generate Synthetic Data", use_container_width=True):
        with st.spinner("Generating SAP IS-U synthetic data..."):
            from src.data_generator import generate_all_data
            all_data = generate_all_data()
            st.session_state.data_generated = True
        st.success("Data generated!")

    # Step 2: Preprocess & EDA
    if st.button("🧹 2. Preprocess & Run EDA", use_container_width=True,
                  disabled=not st.session_state.data_generated):
        with st.spinner("Preprocessing data and running EDA..."):
            from src.data_preprocessing import preprocess_pipeline
            from src.eda import generate_eda_report
            from src.feature_engineering import engineer_features

            merged, features, ids, encoders = preprocess_pipeline()
            generate_eda_report(merged)

            # Feature engineering
            engineered = engineer_features(merged)
            engineered.to_csv(FINAL_FEATURES_FILE, index=False)

            st.session_state.merged_data = merged
        st.success("Preprocessing & EDA complete!")

    # Step 3: Train Models
    if st.button("🤖 3. Train ML Models", use_container_width=True,
                  disabled=not st.session_state.data_generated):
        with st.spinner("Training models (this may take a minute)..."):
            from src.model_training import training_pipeline
            df = pd.read_csv(FINAL_FEATURES_FILE)
            results, trained_models, best_name, scaler = training_pipeline(df)
            st.session_state.models_trained = True
            st.session_state.training_results = results
        st.success(f"Models trained! Best: {best_name}")

    # Step 4: Initialize Chatbot
    if st.button("💬 4. Initialize Chatbot", use_container_width=True,
                  disabled=not st.session_state.models_trained):
        with st.spinner("Loading prediction engine & chatbot..."):
            from src.prediction_engine import ChurnPredictor
            from src.chatbot import RetentionChatbot
            predictor = ChurnPredictor()
            chatbot = RetentionChatbot(predictor)
            st.session_state.predictor = predictor
            st.session_state.chatbot = chatbot
        st.success("Chatbot ready!")

    # Quick run all
    st.markdown("---")
    if st.button("🚀 Run Complete Pipeline", use_container_width=True, type="primary"):
        progress = st.progress(0)
        status = st.empty()
        pipeline_container = st.container()

        with pipeline_container:
            # ── STAGE 1: Data Generation ──
            st.markdown("### 🔄 Stage 1: Generating SAP IS-U Customer Data")
            status.text("Step 1/5: Generating synthetic SAP IS-U data...")
            progress.progress(5)
            from src.data_generator import generate_all_data
            all_data = generate_all_data()
            st.session_state.data_generated = True
            progress.progress(15)

            # Show data preview
            with st.expander("📋 Data Generated — Click to Preview", expanded=True):
                data_cols = st.columns(3)
                with data_cols[0]:
                    st.markdown("**Customer Master** (Business Partners)")
                    st.dataframe(all_data["master"][["customer_id", "customer_name", "age", "region", "service_type", "contract_type", "account_tenure_months", "churned"]].head(5), use_container_width=True, height=200)
                with data_cols[1]:
                    st.markdown("**Billing Records** (DBERCHZ)")
                    st.dataframe(all_data["billing"][["customer_id", "bill_date", "bill_amount", "bill_status", "payment_delay_days"]].head(5), use_container_width=True, height=200)
                with data_cols[2]:
                    st.markdown("**Complaint Data** (with Customer Comments)")
                    st.dataframe(all_data["complaint"][["customer_id", "complaint_category", "severity", "comment"]].head(5), use_container_width=True, height=200)

                st.markdown(f"""
                | Dataset | Records | Description |
                |---------|---------|-------------|
                | Customer Master | {len(all_data['master']):,} | Business partner & contract data |
                | Billing Data | {len(all_data['billing']):,} | Monthly billing records |
                | Consumption Data | {len(all_data['consumption']):,} | Meter readings & usage |
                | Interaction Data | {len(all_data['interaction']):,} | Service interactions |
                | Complaint Data | {len(all_data['complaint']):,} | Complaints with **raw customer comments** |
                | Payment Data | {len(all_data['payment']):,} | Payment transaction records |
                | Demographics | {len(all_data['demographics']):,} | External enrichment data |
                """)

            st.success("✅ Stage 1 Complete — 7 SAP IS-U datasets generated")
            st.markdown("---")

            # ── STAGE 2: NLP Sentiment Analysis ──
            st.markdown("### 🧠 Stage 2: NLP Sentiment Analysis on Customer Comments")
            status.text("Step 2/5: Running VADER sentiment analysis on complaint comments...")
            progress.progress(20)

            st.info("**What's happening:** Every customer complaint comment is analyzed using VADER "
                    "(Valence Aware Dictionary and sEntiment Reasoner) — an NLP engine that reads "
                    "the actual text and scores it from -1.0 (very negative) to +1.0 (very positive).")

            # Show sentiment analysis in action
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            import nltk
            try:
                nltk.data.find("sentiment/vader_lexicon.zip")
            except LookupError:
                nltk.download("vader_lexicon", quiet=True)
            sia = SentimentIntensityAnalyzer()

            # Pick sample comments to demonstrate
            sample_comments = all_data["complaint"]["comment"].drop_duplicates().head(6).tolist()
            with st.expander("🔍 Live Sentiment Analysis — See How Comments Are Scored", expanded=True):
                for i, comment in enumerate(sample_comments):
                    scores = sia.polarity_scores(comment)
                    compound = scores["compound"]
                    if compound >= 0.05:
                        emoji = "🟢"
                        label = "POSITIVE"
                        color = "#27ae60"
                    elif compound <= -0.05:
                        emoji = "🔴"
                        label = "NEGATIVE"
                        color = "#e74c3c"
                    else:
                        emoji = "🟡"
                        label = "NEUTRAL"
                        color = "#f39c12"

                    st.markdown(f"""
                    > *"{comment}"*
                    >
                    > {emoji} **{label}** — Compound Score: <span style="color:{color};font-weight:bold">{compound:+.3f}</span>
                    > &nbsp;&nbsp;|&nbsp;&nbsp;Positive: {scores['pos']:.0%}&nbsp;&nbsp;|&nbsp;&nbsp;Neutral: {scores['neu']:.0%}&nbsp;&nbsp;|&nbsp;&nbsp;Negative: {scores['neg']:.0%}
                    """, unsafe_allow_html=True)

                st.markdown(f"**📊 Total comments analyzed: {len(all_data['complaint']):,}** — "
                            f"Each one scored and aggregated per customer to create sentiment features.")

            st.success("✅ Stage 2 Complete — All customer comments analyzed via NLP")
            st.markdown("---")

            # ── STAGE 3: Preprocessing & Feature Engineering ──
            st.markdown("### ⚙️ Stage 3: Data Preprocessing & Feature Engineering")
            status.text("Step 3/5: Merging data, engineering features, running EDA...")
            progress.progress(35)

            from src.data_preprocessing import preprocess_pipeline
            from src.eda import generate_eda_report
            from src.feature_engineering import engineer_features

            merged, features, ids, encoders = preprocess_pipeline()
            generate_eda_report(merged)
            engineered = engineer_features(merged)
            engineered.to_csv(FINAL_FEATURES_FILE, index=False)
            st.session_state.merged_data = merged
            progress.progress(50)

            with st.expander("🔧 Feature Engineering — What the ML Model Sees", expanded=True):
                st.markdown("All 7 datasets are merged on `customer_id` into a single customer profile. "
                            "Then advanced features are engineered:")

                feature_cats = {
                    "💬 Sentiment Features (from NLP)": [
                        "avg_sentiment_score", "min_sentiment_score", "sentiment_std",
                        "negative_sentiment_ratio", "positive_sentiment_ratio",
                        "avg_sentiment_neg", "avg_sentiment_pos"
                    ],
                    "🚩 Risk Flags": [
                        "payment_risk_flag", "complaint_risk_flag", "low_satisfaction_flag",
                        "high_negative_sentiment_flag", "very_negative_sentiment_flag",
                        "sentiment_volatile_flag", "new_customer_flag", "consumption_declining_flag"
                    ],
                    "📊 Behavioral Features": [
                        "engagement_score", "composite_risk_score",
                        "complaint_rate_per_month", "unresolved_ratio"
                    ],
                }
                for cat_name, cat_cols in feature_cats.items():
                    present_cols = [c for c in cat_cols if c in engineered.columns]
                    if present_cols:
                        st.markdown(f"**{cat_name}**")
                        st.dataframe(engineered[present_cols].describe().round(3), use_container_width=True)

                st.markdown(f"**Total features for ML model: {engineered.shape[1]}** across {engineered.shape[0]:,} customers")

            st.success("✅ Stage 3 Complete — Customer profiles enriched with 40+ features")
            st.markdown("---")

            # ── STAGE 4: Model Training ──
            st.markdown("### 🤖 Stage 4: Training Machine Learning Models")
            status.text("Step 4/5: Training 5 ML models and selecting the best one...")
            progress.progress(55)

            from src.model_training import training_pipeline
            df = pd.read_csv(FINAL_FEATURES_FILE)
            results, trained_models, best_name, scaler = training_pipeline(df)
            st.session_state.models_trained = True
            st.session_state.training_results = results
            progress.progress(80)

            with st.expander("🏆 Model Performance — Which Algorithm Won?", expanded=True):
                st.markdown("Five models were trained and evaluated on held-out test data:")
                results_df = pd.DataFrame(results).T
                st.dataframe(
                    results_df.style.format("{:.4f}").highlight_max(axis=0, color="#90EE90"),
                    use_container_width=True
                )
                st.markdown(f"**🏅 Best Model: `{best_name}`** — selected automatically based on F1 score")

                # Show feature importance if available
                importance_path = os.path.join(REPORT_DIR, "09_feature_importance.png")
                if os.path.exists(importance_path):
                    st.markdown("**Top Features Driving Churn Predictions:**")
                    st.image(importance_path, use_container_width=True)
                    st.caption("Notice how NLP sentiment features contribute to prediction accuracy!")

            st.success(f"✅ Stage 4 Complete — Best model: {best_name}")
            st.markdown("---")

            # ── STAGE 5: Prediction Engine & Chatbot ──
            st.markdown("### 💬 Stage 5: Activating Prediction Engine & AI Chatbot")
            status.text("Step 5/5: Loading prediction engine and AI chatbot...")
            progress.progress(90)

            from src.prediction_engine import ChurnPredictor
            from src.chatbot import RetentionChatbot
            predictor = ChurnPredictor()
            chatbot = RetentionChatbot(predictor)
            st.session_state.predictor = predictor
            st.session_state.chatbot = chatbot
            progress.progress(100)

            # Show quick preview of predictions
            with st.expander("🎯 Prediction Preview — Top At-Risk Customers", expanded=True):
                top_risk = predictor.get_top_risk_customers(5)
                if top_risk:
                    st.markdown("These customers have the **highest churn probability** based on ALL factors "
                                "including their comment sentiment:")
                    for i, c in enumerate(top_risk, 1):
                        prob = c['churn_probability']
                        risk_emoji = "🔴" if c['risk_level'] == "HIGH" else "🟡"
                        st.markdown(f"**{i}. {c['customer_id']}** — {risk_emoji} Churn Probability: "
                                    f"**{prob:.1%}** | Region: {c.get('region', 'N/A')} | "
                                    f"Tenure: {c.get('account_tenure_months', 'N/A')} months")

                st.markdown("")
                st.markdown("**👉 Go to the `AI Chatbot` tab to ask questions in plain English!**")
                st.markdown('*Try: "Show top risk customers" or "Tell me about CUST0000001"*')

            st.success("✅ Stage 5 Complete — System is live!")
            st.markdown("---")

            # ── FINAL: Pipeline Summary ──
            st.balloons()
            st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 2rem; border-radius: 16px; color: white; text-align: center;">
                <h2 style="margin:0; color:white;">🎉 Pipeline Complete!</h2>
                <p style="font-size: 1.1rem; margin-top: 0.5rem; opacity: 0.95;">
                    <strong>5,000 customers</strong> analyzed &nbsp;|&nbsp;
                    <strong>NLP sentiment</strong> extracted from comments &nbsp;|&nbsp;
                    <strong>5 ML models</strong> trained &nbsp;|&nbsp;
                    <strong>AI chatbot</strong> ready
                </p>
                <p style="font-size: 0.95rem; margin-top: 1rem; opacity: 0.85;">
                    Navigate the tabs above to explore the Dashboard, EDA, Models, Customer Lookup, and AI Chatbot
                </p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Upload Custom Data")
    uploaded_files = st.file_uploader(
        "Upload CSV files", type=["csv"], accept_multiple_files=True,
        help="Upload your own CSVs. They will be joined on customer_id."
    )
    if uploaded_files:
        for f in uploaded_files:
            df = pd.read_csv(f)
            save_path = os.path.join(DATA_DIR, f.name)
            os.makedirs(DATA_DIR, exist_ok=True)
            df.to_csv(save_path, index=False)
            st.success(f"Saved: {f.name} ({len(df)} rows)")


# ─── Main Content ────────────────────────────────────────
st.markdown('<div class="main-header">⚡ SAP IS-U Customer Retention Prediction System</div>',
            unsafe_allow_html=True)

# Create tabs
tab_dashboard, tab_eda, tab_models, tab_customers, tab_chatbot = st.tabs([
    "📊 Dashboard", "📈 EDA", "🤖 Models", "👥 Customers", "💬 AI Chatbot"
])


# ─── TAB 1: Dashboard ───────────────────────────────────
with tab_dashboard:
    if st.session_state.predictor:
        predictor = st.session_state.predictor
        summary = predictor.get_data_summary()
        segments = predictor.get_segment_analysis()

        # Metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Customers", f"{summary['total_customers']:,}")
        with col2:
            st.metric("Churn Rate", summary['churn_rate'])
        with col3:
            overall = segments.get('overall', {})
            st.metric("High Risk", f"{overall.get('high_risk_count', 0):,}", delta="⚠️", delta_color="inverse")
        with col4:
            st.metric("Avg Satisfaction", f"{summary['avg_satisfaction']}/5")
        with col5:
            st.metric("Avg Monthly Bill", f"${summary['avg_monthly_bill']:.2f}")

        st.markdown("---")

        # Charts
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Risk Distribution")
            risk_data = {
                "High Risk": overall.get('high_risk_count', 0),
                "Medium Risk": overall.get('medium_risk_count', 0),
                "Low Risk": overall.get('low_risk_count', 0),
            }
            fig, ax = plt.subplots(figsize=(8, 5))
            colors = ['#e74c3c', '#f39c12', '#27ae60']
            ax.pie(risk_data.values(), labels=risk_data.keys(), autopct='%1.1f%%',
                   colors=colors, explode=[0.05, 0, 0], shadow=True, startangle=90)
            ax.set_title("Customer Risk Distribution", fontsize=14, fontweight="bold")
            st.pyplot(fig)
            plt.close()

        with col_right:
            st.subheader("Churn Risk by Region")
            region_data = segments.get("by_region", {})
            if region_data:
                regions = list(region_data.keys())
                probs = [region_data[r]["avg_churn_prob"] for r in regions]
                fig, ax = plt.subplots(figsize=(8, 5))
                bars = ax.bar(regions, probs, color='#3498db', edgecolor='white')
                ax.axhline(y=segments['overall']['avg_churn_prob'], color='red', linestyle='--', label='Overall Avg')
                ax.set_ylabel("Avg Churn Probability")
                ax.set_title("Churn Risk by Region", fontsize=14, fontweight="bold")
                ax.legend()
                plt.xticks(rotation=45, ha='right')
                st.pyplot(fig)
                plt.close()

        # Top risk table
        st.subheader("Top At-Risk Customers")
        top_risk = predictor.get_top_risk_customers(15)
        if top_risk:
            risk_df = pd.DataFrame(top_risk)
            st.dataframe(
                risk_df.style.format({"churn_probability": "{:.2%}"}),
                use_container_width=True, height=400
            )
    else:
        st.info("👈 Click **Run Complete Pipeline** in the sidebar to start the demo.")
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0f3460 0%, #1a1a2e 100%);
                    padding: 2rem; border-radius: 16px; color: white; margin: 1rem 0;">
            <h2 style="color: white; margin-top: 0;">Welcome to the SAP IS-U Customer Retention System</h2>
            <p style="font-size: 1.1rem; opacity: 0.9;">
                This system predicts which utility customers are most likely to leave — <strong>before they actually do</strong>.
                It combines SAP IS-U data with machine learning and NLP to turn raw customer interactions into actionable retention strategies.
            </p>
            <h3 style="color: #667eea; margin-top: 1.5rem;">What You'll See in the Demo:</h3>
            <table style="width: 100%; color: white; font-size: 0.95rem;">
                <tr><td style="padding: 8px 0;">🔄 <strong>Stage 1</strong></td><td>SAP IS-U data is generated (customer master, billing, complaints, payments...)</td></tr>
                <tr><td style="padding: 8px 0;">🧠 <strong>Stage 2</strong></td><td>Customer complaint comments are analyzed using <strong>NLP sentiment analysis</strong></td></tr>
                <tr><td style="padding: 8px 0;">⚙️ <strong>Stage 3</strong></td><td>40+ features are engineered from all data sources including sentiment scores</td></tr>
                <tr><td style="padding: 8px 0;">🤖 <strong>Stage 4</strong></td><td>5 ML models are trained and the best one is selected automatically</td></tr>
                <tr><td style="padding: 8px 0;">💬 <strong>Stage 5</strong></td><td>AI-powered chatbot is activated — ask anything about your customers in plain English</td></tr>
            </table>
            <p style="font-size: 0.95rem; margin-top: 1.5rem; opacity: 0.8;">
                👈 Click <strong>Run Complete Pipeline</strong> to see all stages live.
            </p>
        </div>
        """, unsafe_allow_html=True)


# ─── TAB 2: EDA ─────────────────────────────────────────
with tab_eda:
    st.subheader("Exploratory Data Analysis")

    if os.path.exists(REPORT_DIR):
        plots = sorted([f for f in os.listdir(REPORT_DIR) if f.endswith(".png")])
        if plots:
            for plot in plots:
                st.image(os.path.join(REPORT_DIR, plot), use_container_width=True)
                st.markdown("---")
        else:
            st.info("Run preprocessing & EDA first to see visualizations.")
    else:
        st.info("Run preprocessing & EDA first to see visualizations.")

    # Show statistics if available
    stats_file = os.path.join(REPORT_DIR, "eda_statistics.csv")
    if os.path.exists(stats_file):
        st.subheader("Key Statistical Differences (Churned vs Retained)")
        stats_df = pd.read_csv(stats_file, index_col=0)
        st.dataframe(stats_df.style.format("{:.4f}"), use_container_width=True)


# ─── TAB 3: Models ──────────────────────────────────────
with tab_models:
    st.subheader("Model Training Results")

    if st.session_state.training_results:
        results = st.session_state.training_results
        results_df = pd.DataFrame(results).T

        # Model comparison table
        st.markdown("### Performance Comparison")
        st.dataframe(
            results_df.style.format("{:.4f}").highlight_max(axis=0, color="#90EE90"),
            use_container_width=True
        )

        # Show plots
        model_plots = ["06_model_comparison.png", "07_roc_curves.png",
                       "08_confusion_matrix.png", "09_feature_importance.png"]
        for plot in model_plots:
            path = os.path.join(REPORT_DIR, plot)
            if os.path.exists(path):
                st.image(path, use_container_width=True)
                st.markdown("---")

        # Model results CSV
        results_csv = os.path.join(REPORT_DIR, "model_results.csv")
        if os.path.exists(results_csv):
            st.download_button(
                "📥 Download Model Results CSV",
                open(results_csv).read(),
                file_name="model_results.csv",
                mime="text/csv",
            )
    else:
        st.info("Train models first to see results.")


# ─── TAB 4: Customer Lookup ─────────────────────────────
with tab_customers:
    st.subheader("Customer Churn Risk Lookup")

    if st.session_state.predictor:
        predictor = st.session_state.predictor

        col1, col2 = st.columns([1, 2])
        with col1:
            customer_id = st.text_input("Enter Customer ID", value="CUST0000001",
                                        help="Format: CUST followed by 7 digits")
            search_btn = st.button("🔍 Analyze Customer", type="primary")

        if search_btn and customer_id:
            result = predictor.get_retention_recommendations(customer_id)

            if "error" in result:
                st.error(result["error"])
            else:
                with col2:
                    # Risk indicator
                    risk = result["risk_level"]
                    risk_color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(risk, "⚪")
                    st.markdown(f"### {risk_color} Risk Level: **{risk}**")
                    st.markdown(f"### Churn Probability: **{result['churn_probability']:.1%}**")
                    st.markdown(f"### Prediction: **{result['prediction']}**")

                # Customer details
                st.markdown("---")
                st.markdown("### Customer Profile")
                info = result["customer_info"]
                info_cols = st.columns(4)
                for i, (key, val) in enumerate(info.items()):
                    with info_cols[i % 4]:
                        st.metric(key.replace("_", " ").title(), val)

                # Recommendations
                st.markdown("---")
                st.markdown("### Retention Recommendations")
                for rec in result.get("recommendations", []):
                    priority_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(rec["priority"], "⚪")
                    with st.expander(f"{priority_icon} [{rec['priority']}] {rec['action']}"):
                        st.write(rec["detail"])

        # Bulk search
        st.markdown("---")
        st.subheader("Batch Customer Analysis")
        if st.session_state.merged_data is not None:
            df = st.session_state.merged_data

            # Filters
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                region_filter = st.multiselect("Region", df["region"].unique().tolist())
            with col_f2:
                service_filter = st.multiselect("Service Type", df["service_type"].unique().tolist())
            with col_f3:
                contract_filter = st.multiselect("Contract Type", df["contract_type"].unique().tolist())

            filtered = df.copy()
            if region_filter:
                filtered = filtered[filtered["region"].isin(region_filter)]
            if service_filter:
                filtered = filtered[filtered["service_type"].isin(service_filter)]
            if contract_filter:
                filtered = filtered[filtered["contract_type"].isin(contract_filter)]

            st.dataframe(filtered.head(100), use_container_width=True, height=400)
            st.caption(f"Showing {min(100, len(filtered))} of {len(filtered)} filtered customers")
    else:
        st.info("Initialize the system first to look up customers.")


# ─── TAB 5: AI Chatbot ──────────────────────────────────
with tab_chatbot:
    st.subheader("💬 AI-Powered Retention Analyst")

    if st.session_state.chatbot:
        chatbot = st.session_state.chatbot

        # Chat instructions
        with st.expander("ℹ️ How to use the chatbot", expanded=False):
            st.markdown("""
            **Ask me anything about customer retention!**

            Example questions:
            - "Tell me about CUST0000042"
            - "Show me the top risk customers"
            - "What's the churn rate by region?"
            - "What retention strategies do you recommend?"
            - "Which customer segment has the highest churn?"
            - "Summarize the data for me"
            - "What are the main drivers of churn?"
            """)

        # Display chat history
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if prompt := st.chat_input("Ask about customer retention..."):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    response = chatbot.chat(prompt)
                st.markdown(response)
            st.session_state.chat_messages.append({"role": "assistant", "content": response})

        # Clear chat
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_messages = []
            if chatbot:
                chatbot.clear_history()
            st.rerun()
    else:
        st.info("Initialize the chatbot first from the sidebar.")
        st.markdown("""
        ### Quick Start
        1. Click **Run Complete Pipeline** in the sidebar
        2. Wait for all steps to complete
        3. Start chatting with the AI analyst!
        """)


# ─── Footer ──────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align: center; opacity: 0.6;'>"
    "SAP IS-U Customer Retention Prediction System | "
    "Powered by ML + Claude AI | "
    "Built for Utility Companies"
    "</div>",
    unsafe_allow_html=True,
)
