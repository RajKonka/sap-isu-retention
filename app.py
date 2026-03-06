"""
SAP IS-U Customer Retention Prediction System — V3
Lean version: 3 inputs (Customer Master + Complaints + Interactions)
Full transparency: every step explained
Optional: user-configurable feature weights
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *

st.set_page_config(page_title="SAP IS-U Customer Retention V3", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1a1a2e; text-align: center; padding: 1rem 0; border-bottom: 3px solid #667eea; margin-bottom: 1.5rem; }
    .explain-box { background: #f0f4ff; border-left: 4px solid #667eea; padding: 1rem 1.2rem; border-radius: 0 8px 8px 0; margin: 0.8rem 0; }
    .explain-box h4 { margin: 0 0 0.3rem 0; color: #0f3460; }
    .explain-box p { margin: 0; color: #333; font-size: 0.92rem; }
    .why-box { background: #fff8e1; border-left: 4px solid #f39c12; padding: 0.8rem 1rem; border-radius: 0 8px 8px 0; margin: 0.5rem 0; }
    .why-box p { margin: 0; color: #5d4e37; font-size: 0.9rem; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.2rem; border-radius: 12px; color: white; text-align: center; }
    .metric-card h3 { margin: 0; font-size: 2rem; }
    .metric-card p { margin: 0; opacity: 0.85; font-size: 0.9rem; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f3460 0%, #1a1a2e 100%); }
    div[data-testid="stSidebar"] .stMarkdown { color: white; }
    div[data-testid="stSidebar"] h1, div[data-testid="stSidebar"] h2, div[data-testid="stSidebar"] h3 { color: white; }
</style>
""", unsafe_allow_html=True)


def explain(title, what, why=None, how=None):
    """Render an explanation box."""
    st.markdown(f"""<div class="explain-box"><h4>💡 {title}</h4><p><strong>What:</strong> {what}</p></div>""", unsafe_allow_html=True)
    if why:
        st.markdown(f"""<div class="why-box"><p><strong>Why this matters:</strong> {why}</p></div>""", unsafe_allow_html=True)
    if how:
        st.markdown(f"""<div class="explain-box"><p><strong>How:</strong> {how}</p></div>""", unsafe_allow_html=True)


# ─── Session State ────────────────────────────────────────
for key in ["data_generated", "models_trained", "predictor", "chatbot", "merged_data",
            "training_results", "chat_messages", "use_weights", "feature_weights"]:
    if key not in st.session_state:
        st.session_state[key] = False if key in ["data_generated", "models_trained", "use_weights"] else ([] if key == "chat_messages" else None)


# ─── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("# ⚡ SAP IS-U V3")
    st.markdown("### Customer Retention System")
    st.markdown("*Lean: 3 inputs, full transparency*")
    st.markdown("---")

    api_key = st.text_input("Anthropic API Key (optional)", type="password")
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

    st.markdown("---")

    # ── Optional Weight Configuration ──
    st.session_state.use_weights = st.toggle("⚖️ Enable Feature Weights", value=False,
                                              help="Toggle on to manually adjust how much each feature category influences churn predictions")

    feature_multipliers = None
    if st.session_state.use_weights:
        st.markdown("#### Category Weights")
        st.caption("Adjust importance of each data source. Must total 100%.")

        w_complaint = st.slider("💬 Complaints & Sentiment", 0, 60, 35, key="w_comp",
                                help="How much weight to give complaint data and NLP sentiment scores")
        w_customer = st.slider("👤 Customer Profile", 0, 60, 25, key="w_cust",
                               help="How much weight to give tenure, contract type, demographics")
        w_interaction = st.slider("🤝 Interactions & Service", 0, 60, 25, key="w_int",
                                  help="How much weight to give call frequency, satisfaction, resolution")
        w_engineered = st.slider("🔧 Engineered Risk Flags", 0, 60, 15, key="w_eng",
                                 help="How much weight to give derived risk flags and composite scores")

        total = w_complaint + w_customer + w_interaction + w_engineered
        if total == 100:
            st.success(f"Total: {total}% ✓")
        elif total < 100:
            st.warning(f"Total: {total}% — {100-total}% unassigned")
        else:
            st.error(f"Total: {total}% — exceeds 100%")

        # Build multipliers from category weights
        if total > 0:
            feature_multipliers = {}
            # Map features to categories
            from config import COMPLAINT_FEATURES, SENTIMENT_FEATURES, CUSTOMER_FEATURES, INTERACTION_FEATURES, ENGINEERED_FEATURES
            cat_map = {
                "complaint": (COMPLAINT_FEATURES + SENTIMENT_FEATURES, w_complaint),
                "customer": (CUSTOMER_FEATURES, w_customer),
                "interaction": (INTERACTION_FEATURES, w_interaction),
                "engineered": (ENGINEERED_FEATURES, w_engineered),
            }
            for cat_name, (features, weight) in cat_map.items():
                base = weight / 25.0  # normalize relative to 25% default
                for f in features:
                    feature_multipliers[f] = base

        if st.button("🔄 Reset Weights", use_container_width=True):
            st.rerun()

    st.markdown("---")

    # ── Run Pipeline ──
    if st.button("🚀 Run Complete Pipeline", use_container_width=True, type="primary"):
        progress = st.progress(0)
        status = st.empty()

        # ════════════════════════════════════════════════════
        # STAGE 1: DATA GENERATION
        # ════════════════════════════════════════════════════
        status.text("Stage 1/6: Generating SAP IS-U data...")
        progress.progress(5)

    # We use a flag to trigger pipeline in main content area
        st.session_state._run_pipeline = True
        st.session_state._feature_multipliers = feature_multipliers
        st.rerun()


# ─── Main Content ────────────────────────────────────────
st.markdown('<div class="main-header">⚡ SAP IS-U Customer Retention Prediction System — V3</div>', unsafe_allow_html=True)

# ── Run Pipeline if triggered ──
if getattr(st.session_state, "_run_pipeline", False):
    st.session_state._run_pipeline = False
    feature_multipliers = getattr(st.session_state, "_feature_multipliers", None)

    progress = st.progress(0)
    status = st.empty()

    # ════════════════════════════════════════════════════
    # STAGE 1: DATA GENERATION
    # ════════════════════════════════════════════════════
    st.markdown("## 🔄 Stage 1: Generating SAP IS-U Customer Data")
    explain(
        "What is this step?",
        "We generate synthetic data that mirrors what you would export from a real SAP IS-U system. "
        "In production, this step is replaced by actual CSV exports from SAP transactions (SE16N, CRM_ORDER, etc.).",
        why="We use 3 focused data sources — the ones that directly predict churn. We deliberately excluded "
            "billing detail, consumption readings, and demographics because while useful for other analytics "
            "(like credit scoring), they add noise to churn prediction without proportional value."
    )

    status.text("Stage 1/6: Generating data...")
    progress.progress(5)
    from src.data_generator import generate_all_data
    all_data = generate_all_data()
    st.session_state.data_generated = True
    progress.progress(12)

    # Show the 3 input sources with SAP mapping
    with st.expander("📋 Data Sources — What We Generated", expanded=True):
        for source, sap_info in SAP_TABLE_MAP.items():
            st.markdown(f"**{source.replace('_', ' ').title()}** — SAP: `{sap_info['sap_tables']}`")
            st.caption(sap_info["description"])

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Customer Master**")
            st.dataframe(all_data["master"][["customer_id", "age", "region", "contract_type", "account_tenure_months"]].head(5), use_container_width=True, height=200)
            st.caption(f"{len(all_data['master']):,} customers")
        with c2:
            st.markdown("**Complaints (with comments)**")
            st.dataframe(all_data["complaint"][["customer_id", "complaint_category", "severity", "comment"]].head(5), use_container_width=True, height=200)
            st.caption(f"{len(all_data['complaint']):,} complaint records")
        with c3:
            st.markdown("**Interactions**")
            st.dataframe(all_data["interaction"][["customer_id", "interaction_type", "channel", "satisfaction_score"]].head(5), use_container_width=True, height=200)
            st.caption(f"{len(all_data['interaction']):,} interaction records")

    st.success("✅ Stage 1 Complete — 3 SAP IS-U datasets generated")
    st.markdown("---")

    # ════════════════════════════════════════════════════
    # STAGE 2: DATA CLEANSING
    # ════════════════════════════════════════════════════
    st.markdown("## 🧹 Stage 2: Data Cleansing")
    explain(
        "What is this step?",
        "Raw SAP data contains duplicates, missing values, outliers, and inconsistent formats. "
        "We clean each dataset before analysis to ensure the ML model learns from real patterns, not data errors.",
        why="Garbage in = garbage out. A duplicate customer row would count twice in training. "
            "A missing satisfaction score defaulting to 0 would falsely signal extreme dissatisfaction. "
            "Cleaning prevents the model from learning false patterns."
    )

    status.text("Stage 2/6: Cleaning data...")
    progress.progress(18)
    from src.data_preprocessing import clean_customer_master, clean_complaint_data, clean_interaction_data
    master_clean = clean_customer_master(all_data["master"].copy())
    complaint_clean = clean_complaint_data(all_data["complaint"].copy())
    interaction_clean = clean_interaction_data(all_data["interaction"].copy())

    with st.expander("🧹 Cleansing Details — What We Fixed", expanded=False):
        from src.data_preprocessing import STEP_EXPLANATIONS
        for step_key in ["clean_master", "clean_complaints", "clean_interactions"]:
            info = STEP_EXPLANATIONS[step_key]
            st.markdown(f"**{info['title']}**")
            st.markdown(f"*{info['what']}*")
            for detail in info.get("details", []):
                st.markdown(f"- {detail}")
            st.markdown("")

    st.success("✅ Stage 2 Complete — Data cleaned and validated")
    st.markdown("---")

    # ════════════════════════════════════════════════════
    # STAGE 3: NLP SENTIMENT ANALYSIS
    # ════════════════════════════════════════════════════
    st.markdown("## 🧠 Stage 3: NLP Sentiment Analysis")
    explain(
        "What is this step?",
        "Every customer complaint comment is analyzed using VADER (Valence Aware Dictionary and sEntiment Reasoner). "
        "VADER reads the actual text and scores it from -1.0 (very negative) to +1.0 (very positive).",
        why="A severity code of '4' tells you the complaint is serious. But it doesn't tell you the customer "
            "said 'I want to cancel immediately, this is disgusting.' NLP captures the emotional intensity "
            "that structured SAP data misses. Customers who use very negative language churn at 2-3× the average rate.",
        how="VADER has 7,500+ words rated by human linguists. It handles intensifiers ('very frustrated' scores worse "
            "than 'frustrated'), negations ('not happy' flips positive to negative), and outputs a compound score from -1 to +1."
    )

    status.text("Stage 3/6: Running NLP sentiment analysis...")
    progress.progress(25)

    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    import nltk
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)
    sia = SentimentIntensityAnalyzer()

    sample_comments = complaint_clean["comment"].drop_duplicates().head(6).tolist()
    with st.expander("🔍 Live Sentiment Scoring — Watch VADER Analyze Comments", expanded=True):
        for comment in sample_comments:
            scores = sia.polarity_scores(comment)
            compound = scores["compound"]
            emoji = "🟢" if compound >= 0.05 else ("🔴" if compound <= -0.05 else "🟡")
            label = "POSITIVE" if compound >= 0.05 else ("NEGATIVE" if compound <= -0.05 else "NEUTRAL")
            color = "#27ae60" if compound >= 0.05 else ("#e74c3c" if compound <= -0.05 else "#f39c12")
            st.markdown(f'> *"{comment}"*\n>\n> {emoji} **{label}** — Score: '
                        f'<span style="color:{color};font-weight:bold">{compound:+.3f}</span>'
                        f' &nbsp;|&nbsp; Pos: {scores["pos"]:.0%} &nbsp;|&nbsp; Neu: {scores["neu"]:.0%}'
                        f' &nbsp;|&nbsp; Neg: {scores["neg"]:.0%}', unsafe_allow_html=True)
        st.markdown(f"**Total comments to analyze: {len(complaint_clean):,}**")

    st.success("✅ Stage 3 Complete — All comments scored")
    st.markdown("---")

    # ════════════════════════════════════════════════════
    # STAGE 4: PREPROCESSING + FEATURE ENGINEERING
    # ════════════════════════════════════════════════════
    st.markdown("## ⚙️ Stage 4: Feature Engineering")
    explain(
        "What is this step?",
        "We merge all 3 data sources on customer_id, aggregate complaint and interaction records per customer, "
        "and create new derived features (risk flags, engagement scores, composite risk) that don't exist in the raw data.",
        why="Raw data tells you 'Customer X had 5 complaints.' Feature engineering tells you "
            "'Customer X has high complaint frequency, deeply negative sentiment, low satisfaction, and 3 unresolved issues — "
            "composite risk score: 6/8.' This transforms data into predictive signals.",
        how="Each customer gets one row with ~35 features: original attributes + aggregated stats + NLP scores + risk flags."
    )

    status.text("Stage 4/6: Engineering features...")
    progress.progress(35)

    from src.data_preprocessing import preprocess_pipeline
    from src.eda import generate_eda_report
    from src.feature_engineering import engineer_features, FEATURE_EXPLANATIONS

    merged, features, ids, _ = preprocess_pipeline()
    generate_eda_report(merged)
    engineered = engineer_features(merged, feature_multipliers)
    st.session_state.merged_data = merged
    progress.progress(50)

    with st.expander("🔧 Engineered Features — What We Created & Why", expanded=True):
        st.markdown("Each new feature is created for a specific reason:")
        for feat_name, feat_info in FEATURE_EXPLANATIONS.items():
            st.markdown(f"**`{feat_name}`** — {feat_info['what']}")
            st.markdown(f"- *How:* {feat_info['how']}")
            st.markdown(f"- *Why:* {feat_info['why']}")
            st.markdown("")

        st.markdown(f"**Total features for ML model: {engineered.shape[1] - 3}** (excluding customer_id, name, churned)")

        # Show feature stats
        risk_flags = [c for c in engineered.columns if c.endswith("_flag")]
        if risk_flags:
            st.markdown("**Risk Flag Summary:**")
            flag_data = {f: f"{engineered[f].mean():.1%}" for f in risk_flags}
            st.dataframe(pd.DataFrame({"Flag": flag_data.keys(), "% Customers Flagged": flag_data.values()}), use_container_width=True)

    if feature_multipliers:
        with st.expander("⚖️ Weight Multipliers Applied", expanded=False):
            st.markdown("Your custom weights adjusted feature importance:")
            weight_df = pd.DataFrame({"Feature": feature_multipliers.keys(), "Multiplier": [f"{v:.2f}×" for v in feature_multipliers.values()]})
            st.dataframe(weight_df, use_container_width=True)

    st.success("✅ Stage 4 Complete — Features engineered")
    st.markdown("---")

    # ════════════════════════════════════════════════════
    # STAGE 5: MODEL TRAINING
    # ════════════════════════════════════════════════════
    st.markdown("## 🤖 Stage 5: ML Model Training")
    explain(
        "What is this step?",
        "We train 5 different ML models on the engineered features and compare their performance. "
        "The best model is automatically selected based on ROC AUC score.",
        why="Different algorithms have different strengths. Logistic Regression is fast and interpretable. "
            "Random Forest handles messy data. Gradient Boosting finds subtle patterns. By comparing all of them, "
            "we ensure we pick the most accurate one for this specific dataset.",
        how="Data is split 80/20 (train/test). Each model trains on 80%, predicts on the held-out 20%. "
            "5-fold cross-validation provides additional robustness. We measure accuracy, precision, recall, F1, and ROC AUC."
    )

    status.text("Stage 5/6: Training ML models...")
    progress.progress(55)

    from src.model_training import training_pipeline, TRAINING_EXPLANATIONS
    df = pd.read_csv(FINAL_FEATURES_FILE)
    results, trained_models, best_name, scaler = training_pipeline(df, feature_multipliers)
    st.session_state.models_trained = True
    st.session_state.training_results = results
    progress.progress(85)

    with st.expander("🏆 Model Results — What Each Model Does & How It Performed", expanded=True):
        # Explain each model
        for model_key, model_info in TRAINING_EXPLANATIONS.items():
            if model_key == "metrics":
                continue
            st.markdown(f"**{model_key.replace('_', ' ').title()}** — {model_info['what']}")
            st.caption(f"Strength: {model_info['strength']} | Weakness: {model_info['weakness']}")

        st.markdown("---")
        st.markdown("**Performance Comparison:**")
        results_df = pd.DataFrame(results).T
        st.dataframe(results_df.style.format("{:.4f}").highlight_max(axis=0, color="#90EE90"), use_container_width=True)

        st.markdown("**What do these metrics mean?**")
        for metric, explanation in TRAINING_EXPLANATIONS["metrics"].items():
            st.markdown(f"- **{metric}**: {explanation}")

        st.markdown(f"\n**🏅 Best Model: `{best_name}`**")

        importance_path = os.path.join(REPORT_DIR, "09_feature_importance.png")
        if os.path.exists(importance_path):
            st.markdown("**Which features drove the predictions?**")
            st.image(importance_path, use_container_width=True)

    st.success(f"✅ Stage 5 Complete — Best model: {best_name}")
    st.markdown("---")

    # ════════════════════════════════════════════════════
    # STAGE 6: PREDICTION ENGINE + CHATBOT
    # ════════════════════════════════════════════════════
    st.markdown("## 💬 Stage 6: Prediction Engine & AI Chatbot")
    explain(
        "What is this step?",
        "The trained model is loaded into a prediction engine that can score any customer in real-time. "
        "The AI chatbot lets you ask questions in plain English about customer risk.",
        why="This is where the system becomes actionable. Instead of looking at spreadsheets, "
            "a retention manager can type 'Show me top 10 at-risk customers in the Northeast' and get an instant answer.",
    )

    status.text("Stage 6/6: Loading prediction engine...")
    progress.progress(92)

    from src.prediction_engine import ChurnPredictor
    from src.chatbot import RetentionChatbot
    predictor = ChurnPredictor()
    chatbot = RetentionChatbot(predictor)
    st.session_state.predictor = predictor
    st.session_state.chatbot = chatbot
    progress.progress(100)

    with st.expander("🎯 Top At-Risk Customers", expanded=True):
        top_risk = predictor.get_top_risk_customers(5)
        if top_risk:
            for i, c in enumerate(top_risk, 1):
                prob = c["churn_probability"]
                emoji = "🔴" if c["risk_level"] == "HIGH" else "🟡"
                st.markdown(f"**{i}. {c['customer_id']}** — {emoji} **{prob:.1%}** churn probability | "
                            f"Region: {c.get('region', 'N/A')} | Tenure: {c.get('account_tenure_months', 'N/A')} months")
        st.markdown("**👉 Go to the AI Chatbot tab to ask questions!**")

    st.success("✅ Pipeline Complete!")
    st.balloons()
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 16px; color: white; text-align: center;">
        <h2 style="margin:0; color:white;">🎉 V3 Pipeline Complete!</h2>
        <p style="font-size: 1.1rem; margin-top: 0.5rem; opacity: 0.95;">
            <strong>3 focused inputs</strong> &nbsp;|&nbsp; <strong>NLP sentiment</strong> on every comment &nbsp;|&nbsp;
            <strong>5 ML models</strong> compared &nbsp;|&nbsp; <strong>Full transparency</strong> at every step
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─── Tabs ─────────────────────────────────────────────────
tab_dash, tab_eda, tab_models, tab_customers, tab_chatbot, tab_upload = st.tabs([
    "📊 Dashboard", "📈 EDA", "🤖 Models", "👥 Customers", "💬 AI Chatbot", "📂 Upload Data"
])

with tab_dash:
    if st.session_state.predictor:
        predictor = st.session_state.predictor
        summary = predictor.get_data_summary()
        segments = predictor.get_segment_analysis()
        overall = segments.get("overall", {})

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Total Customers", f"{summary['total_customers']:,}")
        with c2: st.metric("Churn Rate", summary["churn_rate"])
        with c3: st.metric("High Risk", f"{overall.get('high_risk_count', 0):,}")
        with c4: st.metric("Avg Satisfaction", f"{summary['avg_satisfaction']}/5")
        st.markdown("---")

        cl, cr = st.columns(2)
        with cl:
            st.subheader("Risk Distribution")
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.pie([overall.get("high_risk_count", 0), overall.get("medium_risk_count", 0), overall.get("low_risk_count", 0)],
                   labels=["High", "Medium", "Low"], autopct="%1.1f%%", colors=["#e74c3c", "#f39c12", "#27ae60"], explode=[0.05, 0, 0])
            ax.set_title("Risk Distribution", fontsize=14, fontweight="bold")
            st.pyplot(fig); plt.close()
        with cr:
            st.subheader("Churn by Region")
            rd = segments.get("by_region", {})
            if rd:
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.bar(rd.keys(), [rd[r]["avg_churn_prob"] for r in rd], color="#667eea")
                ax.axhline(y=overall["avg_churn_prob"], color="red", linestyle="--", label="Avg")
                ax.set_ylabel("Avg Churn Prob"); ax.legend(); plt.xticks(rotation=45, ha="right")
                st.pyplot(fig); plt.close()

        st.subheader("Top At-Risk Customers")
        top = predictor.get_top_risk_customers(15)
        if top:
            st.dataframe(pd.DataFrame(top).style.format({"churn_probability": "{:.2%}"}), use_container_width=True)
    else:
        st.info("👈 Click **Run Complete Pipeline** in the sidebar to start.")

with tab_eda:
    st.subheader("Exploratory Data Analysis")
    if os.path.exists(REPORT_DIR):
        plots = sorted([f for f in os.listdir(REPORT_DIR) if f.endswith(".png") and f.startswith(("01", "02", "03", "04", "05"))])
        for plot in plots:
            st.image(os.path.join(REPORT_DIR, plot), use_container_width=True)
            st.markdown("---")
    else:
        st.info("Run the pipeline to generate EDA visualizations.")

with tab_models:
    st.subheader("Model Training Results")
    if st.session_state.training_results:
        results_df = pd.DataFrame(st.session_state.training_results).T
        st.dataframe(results_df.style.format("{:.4f}").highlight_max(axis=0, color="#90EE90"), use_container_width=True)
        for plot in ["06_model_comparison.png", "07_roc_curves.png", "08_confusion_matrix.png", "09_feature_importance.png"]:
            path = os.path.join(REPORT_DIR, plot)
            if os.path.exists(path):
                st.image(path, use_container_width=True); st.markdown("---")
    else:
        st.info("Train models first.")

with tab_customers:
    st.subheader("Customer Churn Risk Lookup")
    if st.session_state.predictor:
        predictor = st.session_state.predictor
        c1, c2 = st.columns([1, 2])
        with c1:
            cid = st.text_input("Enter Customer ID", value="CUST0000001")
            search = st.button("🔍 Analyze", type="primary")
        if search and cid:
            result = predictor.get_retention_recommendations(cid)
            if "error" in result:
                st.error(result["error"])
            else:
                with c2:
                    risk_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(result["risk_level"], "⚪")
                    st.markdown(f"### {risk_emoji} Risk: **{result['risk_level']}** | Churn: **{result['churn_probability']:.1%}**")
                st.markdown("---")
                info = result["customer_info"]
                cols = st.columns(4)
                for i, (k, v) in enumerate(info.items()):
                    with cols[i % 4]: st.metric(k.replace("_", " ").title(), v)
                st.markdown("---")
                st.markdown("### Retention Recommendations")
                for rec in result.get("recommendations", []):
                    icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(rec["priority"], "⚪")
                    with st.expander(f"{icon} [{rec['priority']}] {rec['action']}"):
                        st.write(rec["detail"])
    else:
        st.info("Run the pipeline first.")

with tab_chatbot:
    st.subheader("💬 AI-Powered Retention Analyst")
    if st.session_state.chatbot:
        chatbot = st.session_state.chatbot
        with st.expander("ℹ️ How to use", expanded=False):
            st.markdown("**Try:** 'Tell me about CUST0000042', 'Show top risk customers', 'Summarize the data'")
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        if prompt := st.chat_input("Ask about customer retention..."):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."): response = chatbot.chat(prompt)
                st.markdown(response)
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_messages = []
            chatbot.clear_history(); st.rerun()
    else:
        st.info("Run the pipeline first to activate the chatbot.")
        
with tab_upload:
    from src.upload_tab import render_upload_tab
    render_upload_tab()

st.markdown("---")
st.markdown('<div style="text-align:center;opacity:0.6;">SAP IS-U Customer Retention V3 | ML + NLP + Claude AI | Lean: 3 Inputs, Full Transparency</div>', unsafe_allow_html=True)
