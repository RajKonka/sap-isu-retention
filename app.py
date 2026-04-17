"""
SAP IS-U Customer Retention Prediction System — Production
Customer-facing version: no technical details exposed
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *

st.set_page_config(page_title="Customer Retention Predictor", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1a1a2e; text-align: center; padding: 1rem 0; border-bottom: 3px solid #667eea; margin-bottom: 1.5rem; }
    .stage-box { background: #f0f4ff; border-left: 4px solid #667eea; padding: 0.8rem 1.2rem; border-radius: 0 8px 8px 0; margin: 0.8rem 0; }
    .stage-box p { margin: 0; color: #333; font-size: 0.92rem; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.2rem; border-radius: 12px; color: white; text-align: center; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f3460 0%, #1a1a2e 100%); }
    div[data-testid="stSidebar"] .stMarkdown { color: white; }
    div[data-testid="stSidebar"] h1, div[data-testid="stSidebar"] h2, div[data-testid="stSidebar"] h3 { color: white; }
    button[data-baseweb="tab"] { font-size: 1.08rem !important; font-weight: 600 !important; padding: 0.7rem 1.4rem !important; }
    div[data-baseweb="tab-list"] { gap: 0.25rem; margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)

def stage_msg(text):
    st.markdown(f'<div class="stage-box"><p>{text}</p></div>', unsafe_allow_html=True)

# ─── Session State ────────────────────────────────────────
for key in ["data_generated", "models_trained", "predictor", "chatbot", "merged_data",
            "training_results", "chat_messages", "use_weights", "feature_weights"]:
    if key not in st.session_state:
        st.session_state[key] = False if key in ["data_generated", "models_trained", "use_weights"] else ([] if key == "chat_messages" else None)

# ─── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("# ⚡ Vantive Inc")
    st.markdown("### Customer Retention Predictor")
    st.markdown("---")

    nuro_key = st.text_input("NuroStudio API Key", type="password",
        help="Connect to NuroStudio for private AI")
    if nuro_key:
        os.environ["NUROSTUDIO_API_KEY"] = nuro_key

    with st.expander("Other API Keys", expanded=False):
        claude_key = st.text_input("Claude API Key (optional)", type="password")
        if claude_key:
            os.environ["ANTHROPIC_API_KEY"] = claude_key

    st.markdown("---")

    if st.button("🚀 Run Demo", use_container_width=True, type="primary"):
        st.session_state._run_pipeline = True
        st.rerun()

# ─── Main Content ────────────────────────────────────────
st.markdown('<div class="main-header">⚡ Customer Retention Prediction System</div>', unsafe_allow_html=True)

# ─── Tabs (always at top) ─────────────────────────────────
tab_dash, tab_eda, tab_customers, tab_chatbot, tab_upload = st.tabs([
    "📊 Dashboard", "📈 Insights", "👥 Customer Lookup", "💬 AI Assistant", "📂 Upload Your Data"
])

with tab_dash:
    # ── Run Pipeline ──
    if getattr(st.session_state, "_run_pipeline", False):
        st.session_state._run_pipeline = False

        progress = st.progress(0)
        status = st.empty()

        # ════════════════════════════════════════════════════
        # STAGE 1: DATA
        # ════════════════════════════════════════════════════
        st.markdown("## 🔄 Loading Customer Data")
        stage_msg("Preparing customer profiles, service records, and feedback data...")

        status.text("Loading data...")
        progress.progress(5)
        from src.data_generator import generate_all_data
        all_data = generate_all_data()
        st.session_state.data_generated = True
        progress.progress(12)

        with st.expander("📋 Data Loaded — Preview", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Customer Profiles**")
                st.dataframe(all_data["master"][["customer_id", "region", "contract_type", "account_tenure_months"]].head(5), use_container_width=True, height=200)
                st.caption(f"{len(all_data['master']):,} customers")
            with c2:
                st.markdown("**Customer Feedback**")
                st.dataframe(all_data["complaint"][["customer_id", "complaint_category", "severity"]].head(5), use_container_width=True, height=200)
                st.caption(f"{len(all_data['complaint']):,} feedback records")
            with c3:
                st.markdown("**Service History**")
                st.dataframe(all_data["interaction"][["customer_id", "interaction_type", "channel"]].head(5), use_container_width=True, height=200)
                st.caption(f"{len(all_data['interaction']):,} interactions")

        st.success("✅ Customer data loaded successfully")
        st.markdown("---")

        # ════════════════════════════════════════════════════
        # STAGE 2: CLEANSING
        # ════════════════════════════════════════════════════
        st.markdown("## 🧹 Validating & Cleaning Data")
        stage_msg("Removing duplicates, fixing inconsistencies, and validating all records...")

        status.text("Cleaning data...")
        progress.progress(18)
        from src.data_preprocessing import clean_customer_master, clean_complaint_data, clean_interaction_data
        master_clean = clean_customer_master(all_data["master"].copy())
        complaint_clean = clean_complaint_data(all_data["complaint"].copy())
        interaction_clean = clean_interaction_data(all_data["interaction"].copy())

        st.success("✅ Data validated and cleaned")
        st.markdown("---")

        # ════════════════════════════════════════════════════
        # STAGE 3: AI ANALYSIS
        # ════════════════════════════════════════════════════
        st.markdown("## 🧠 Analyzing Customer Feedback")
        stage_msg("Our AI is reading every customer comment and scoring their satisfaction level...")

        status.text("Analyzing customer feedback...")
        progress.progress(25)

        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        import nltk
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            nltk.download("vader_lexicon", quiet=True)
        sia = SentimentIntensityAnalyzer()

        sample_comments = complaint_clean["comment"].drop_duplicates().head(4).tolist()
        with st.expander("🔍 See How Our AI Reads Customer Feedback", expanded=True):
            for comment in sample_comments:
                scores = sia.polarity_scores(comment)
                compound = scores["compound"]
                emoji = "🟢" if compound >= 0.05 else ("🔴" if compound <= -0.05 else "🟡")
                label = "Happy" if compound >= 0.05 else ("Unhappy" if compound <= -0.05 else "Neutral")
                color = "#27ae60" if compound >= 0.05 else ("#e74c3c" if compound <= -0.05 else "#f39c12")
                st.markdown(f'> *"{comment}"*\n>\n> {emoji} **{label}**', unsafe_allow_html=True)
            st.markdown(f"**{len(complaint_clean):,} customer comments analyzed**")

        st.success("✅ Customer feedback analysis complete")
        st.markdown("---")

        # ════════════════════════════════════════════════════
        # STAGE 4: BUILDING PROFILES
        # ════════════════════════════════════════════════════
        st.markdown("## ⚙️ Building Customer Risk Profiles")
        stage_msg("Combining all data sources into comprehensive customer profiles with risk indicators...")

        status.text("Building risk profiles...")
        progress.progress(35)

        from src.data_preprocessing import preprocess_pipeline
        from src.eda import generate_eda_report
        from src.feature_engineering import engineer_features

        merged, features, ids, _ = preprocess_pipeline()
        generate_eda_report(merged)
        engineered = engineer_features(merged)
        st.session_state.merged_data = merged
        progress.progress(50)

        with st.expander("📊 Profile Summary", expanded=False):
            risk_flags = [c for c in engineered.columns if c.endswith("_flag")]
            if risk_flags:
                n_flagged = {f.replace("_flag", "").replace("_", " ").title(): f"{engineered[f].mean():.0%}" for f in risk_flags}
                st.markdown("**Risk indicators detected across your customer base:**")
                for name, pct in n_flagged.items():
                    st.markdown(f"- {name}: **{pct}** of customers flagged")
            st.markdown(f"**{engineered.shape[0]:,} customer profiles built**")

        st.success("✅ Customer risk profiles ready")
        st.markdown("---")

        # ════════════════════════════════════════════════════
        # STAGE 5: PREDICTION
        # ════════════════════════════════════════════════════
        st.markdown("## 🤖 Training Prediction Models")
        stage_msg("Our AI is learning patterns from your data to predict which customers are at risk...")

        status.text("Training prediction models...")
        progress.progress(55)

        from src.model_training import training_pipeline
        df = pd.read_csv(FINAL_FEATURES_FILE)
        results, trained_models, best_name, scaler = training_pipeline(df)
        st.session_state.models_trained = True
        st.session_state.training_results = results
        progress.progress(85)

        with st.expander("📈 Prediction Accuracy", expanded=True):
            results_df = pd.DataFrame(results).T
            best_metrics = results_df.loc[best_name]
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Accuracy", f"{best_metrics['accuracy']:.0%}")
            with c2:
                st.metric("Precision", f"{best_metrics['precision']:.0%}")
            with c3:
                st.metric("Detection Rate", f"{best_metrics['recall']:.0%}")
            st.caption("Our AI was tested on held-out data it never saw during training")

        st.success("✅ Prediction models trained successfully")
        st.markdown("---")

        # ════════════════════════════════════════════════════
        # STAGE 6: GO LIVE
        # ════════════════════════════════════════════════════
        st.markdown("## 💬 System Ready")
        stage_msg("Loading prediction engine and AI assistant...")

        status.text("Going live...")
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
                    st.markdown(f"**{i}. {c['customer_id']}** — {emoji} **{prob:.1%}** risk | "
                                f"Region: {c.get('region', 'N/A')} | Tenure: {c.get('account_tenure_months', 'N/A')} months")
            st.markdown("**👉 Use the tabs above to explore Insights, Customer Lookup, and the AI Assistant.**")

        st.success("✅ System is live!")
        st.balloons()
        st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 16px; color: white; text-align: center;">
        <h2 style="margin:0; color:white;">🎉 Ready!</h2>
        <p style="font-size: 1.1rem; margin-top: 0.5rem; opacity: 0.95;">
            Your customer retention system is now active. Use the tabs at the top to explore Insights, look up individual customers, or chat with the AI assistant.
        </p>
    </div>
        """, unsafe_allow_html=True)

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
            ax.set_title("Customer Risk Distribution", fontsize=14, fontweight="bold")
            st.pyplot(fig); plt.close()
        with cr:
            st.subheader("Risk by Region")
            rd = segments.get("by_region", {})
            if rd:
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.bar(rd.keys(), [rd[r]["avg_churn_prob"] for r in rd], color="#667eea")
                ax.axhline(y=overall["avg_churn_prob"], color="red", linestyle="--", label="Average")
                ax.set_ylabel("Risk Score"); ax.legend(); plt.xticks(rotation=45, ha="right")
                st.pyplot(fig); plt.close()

        st.subheader("Highest Risk Customers")
        top = predictor.get_top_risk_customers(15)
        if top:
            rdf = pd.DataFrame(top)
            display_cols = [c for c in ["customer_id", "churn_probability", "risk_level", "region", "account_tenure_months"] if c in rdf.columns]
            st.dataframe(rdf[display_cols].style.format({"churn_probability": "{:.1%}"}), use_container_width=True)
    else:
        st.info("👈 Click **Run Demo** in the sidebar to see the system in action.")
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0f3460 0%, #1a1a2e 100%); padding: 2rem; border-radius: 16px; color: white; margin: 1rem 0;">
            <h2 style="color: white; margin-top: 0;">Predict Customer Churn Before It Happens</h2>
            <p style="font-size: 1.1rem; opacity: 0.9;">
                Our AI analyzes your customer data — profiles, feedback, and service history — to identify 
                who is most likely to leave. Get actionable insights and retention recommendations.
            </p>
            <p style="opacity: 0.7; margin-top: 1rem;">Click <strong>Run Demo</strong> to see it with sample data, or go to <strong>Upload Your Data</strong> to try with your own.</p>
        </div>
        """, unsafe_allow_html=True)

with tab_eda:
    st.subheader("Customer Insights")
    if os.path.exists(REPORT_DIR):
        try:
            plots = sorted([f for f in os.listdir(REPORT_DIR) if f.endswith(".png")])
            if plots:
                for plot in plots:
                    st.image(os.path.join(REPORT_DIR, plot), use_container_width=True)
                    st.markdown("---")
            else:
                st.info("No insight charts yet — run the demo to generate them.")
        except Exception as e:
            st.error(f"Could not load charts: {e}")
    else:
        st.markdown("""
        <div style="background:#f0f4ff;border:2px dashed #667eea;border-radius:12px;padding:2rem;text-align:center;margin:2rem 0;">
            <h3 style="color:#667eea;margin:0 0 0.5rem 0;">📈 Insights not generated yet</h3>
            <p style="color:#555;margin:0;">Click <strong>Run Demo</strong> in the sidebar to analyse sample data and populate this tab.</p>
        </div>
        """, unsafe_allow_html=True)

with tab_customers:
    st.subheader("Customer Risk Lookup")
    if st.session_state.predictor:
        predictor = st.session_state.predictor
        c1, c2 = st.columns([1, 2])
        with c1:
            cid = st.text_input("Customer ID", value="CUST0000001")
            search = st.button("🔍 Analyze", type="primary")
        if search and cid:
            result = predictor.get_retention_recommendations(cid)
            if "error" in result:
                with c2:
                    st.error(f"Customer **{cid}** not found. Check the ID and try again.")
            else:
                with c2:
                    risk_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(result["risk_level"], "⚪")
                    st.markdown(f"### {risk_emoji} Risk: **{result['risk_level']}** | Churn Probability: **{result['churn_probability']:.1%}**")
                st.markdown("---")
                info = result["customer_info"]
                cols = st.columns(4)
                for i, (k, v) in enumerate(info.items()):
                    with cols[i % 4]: st.metric(k.replace("_", " ").title(), v)
                st.markdown("---")
                st.markdown("### Recommended Actions")
                for rec in result.get("recommendations", []):
                    icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(rec["priority"], "⚪")
                    with st.expander(f"{icon} {rec['action']}"):
                        st.write(rec["detail"])
    else:
        st.markdown("""
        <div style="background:#f0f4ff;border:2px dashed #667eea;border-radius:12px;padding:2rem;text-align:center;margin:2rem 0;">
            <h3 style="color:#667eea;margin:0 0 0.5rem 0;">👥 Customer lookup not available yet</h3>
            <p style="color:#555;margin:0;">Click <strong>Run Demo</strong> in the sidebar to load customer data first.</p>
        </div>
        """, unsafe_allow_html=True)

with tab_chatbot:
    st.subheader("💬 AI Retention Assistant")
    if st.session_state.chatbot:
        chatbot = st.session_state.chatbot
        mode_colors = {"nurostudio": "#27ae60", "claude": "#667eea", "fallback": "#888"}
        mode_color = mode_colors.get(chatbot.mode, "#888")
        st.markdown(f'<span style="background:{mode_color};color:white;padding:2px 10px;border-radius:12px;font-size:0.8rem;">● {chatbot.get_mode_label()}</span>', unsafe_allow_html=True)
        with st.expander("💡 What can I ask?", expanded=False):
            st.markdown("""
            - "Show me the top 10 at-risk customers"
            - "Tell me about CUST0000042"
            - "What's the churn rate by region?"
            - "What retention strategies do you recommend?"
            """)
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        if prompt := st.chat_input("Ask about your customers..."):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."): response = chatbot.chat(prompt)
                st.markdown(response)
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_messages = []
            chatbot.clear_history(); st.rerun()
    else:
        st.markdown("""
        <div style="background:#f0f4ff;border:2px dashed #667eea;border-radius:12px;padding:2rem;text-align:center;margin:2rem 0;">
            <h3 style="color:#667eea;margin:0 0 0.5rem 0;">💬 AI Assistant not active yet</h3>
            <p style="color:#555;margin:0;">Click <strong>Run Demo</strong> in the sidebar to initialise the assistant.</p>
        </div>
        """, unsafe_allow_html=True)

with tab_upload:
    from src.upload_tab import render_upload_tab
    from src.registration import is_registered, render_registration_gate, check_data_limit, render_upgrade_wall
    
    if not is_registered():
        render_registration_gate()
    else:
        render_upload_tab()

st.markdown("---")
st.markdown('<div style="text-align:center;opacity:0.5;font-size:0.85rem;">Customer Retention Prediction System | Powered by Vantive Inc</div>', unsafe_allow_html=True)
