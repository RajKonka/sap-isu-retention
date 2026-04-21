"""
Upload Tab UI — Production
Hybrid: Predict Only + Optional Retrain
Includes 5,000 customer limit and registration gate integration
"""
import streamlit as st
import pandas as pd
import numpy as np
import os, sys, joblib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *
from src.data_upload import (
    read_file, auto_detect_table_type, auto_map_columns,
    transform_dataframe, generate_missing_data, infer_churn_labels,
    EXPECTED_SCHEMAS,
)
from src.registration import check_data_limit, render_upgrade_wall, FREE_TIER_LIMIT

MAX_UPLOAD_MB = 50
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Permanent pre-trained base model — used by Predict Only mode
BASE_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "base")


def _base_model_exists():
    """True when the permanent base model files are present on disk."""
    required = ["best_model.pkl", "scaler.pkl", "model_metadata.pkl"]
    return all(os.path.exists(os.path.join(BASE_MODEL_DIR, f)) for f in required)

def _render_history():
    """Show previous run history for this user."""
    import json
    path = _history_file()
    if not os.path.exists(path):
        return
    try:
        history = json.loads(open(path).read())
    except Exception:
        return
    if not history:
        return

    with st.expander(f"🕘 Your Previous Runs ({len(history)})", expanded=False):
        for i, run in enumerate(history):
            ts = run.get("timestamp", "")[:16].replace("T", " at ")
            total = run.get("total", 0)
            high  = run.get("high_risk", 0)
            med   = run.get("medium_risk", 0)
            low   = run.get("low_risk", 0)
            avg   = run.get("avg_churn_prob", 0)
            label = "**Latest run**" if i == 0 else f"Run {i + 1}"
            st.markdown(
                f"{label} — {ts}  \n"
                f"📊 {total:,} customers · 🔴 {high} high · 🟡 {med} medium · 🟢 {low} low · "
                f"avg risk {avg:.1%}"
            )
        if os.path.exists(_last_results_file()):
            last_res = pd.read_csv(_last_results_file())
            st.download_button(
                "📥 Re-download Last Results (CSV)",
                last_res.to_csv(index=False),
                "last_results.csv", "text/csv",
            )


def render_upload_tab():
    st.subheader("📂 Upload Your Own Data")

    # Restore last run from disk when user logs back in
    restore_session_from_disk()

    has_base = _base_model_exists()
    if has_base:
        st.markdown('<div style="background:#ecfdf5;border-left:4px solid #27ae60;padding:1rem;border-radius:0 8px 8px 0;margin-bottom:1rem;"><strong>✅ System is ready.</strong> Predict Only scores your customers against our pre-trained utility industry baseline model (15,000 customers, ROC AUC 0.80). Upload all three files for best accuracy.</div>', unsafe_allow_html=True)
    else:
        st.error("Base model not found. Please contact support or re-deploy the application.")

    _render_history()

    st.markdown("**Upload up to 3 file types — Excel or CSV works best. Column names don't need to match exactly, we'll auto-detect.**")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
**👤 Customer Profiles**
Required: `customer_id`
Optional: `customer_name`, `region`, `contract_type`, `service_type`, `age`, `gender`, `account_tenure_months`, `income_bracket`, `has_autopay`
        """)
    with col2:
        st.markdown("""
**💬 Feedback / Complaints**
Required: `customer_id`, `comment`
Optional: `complaint_date`, `complaint_category`, `severity`, `escalated`, `resolved`, `resolution_time_days`
        """)
    with col3:
        st.markdown("""
**📞 Service Interactions**
Required: `customer_id`
Optional: `interaction_date`, `interaction_type`, `channel`, `duration_minutes`, `satisfaction_score`, `resolved`
        """)
    st.caption(f"You can upload just one file — e.g. a customer list with feedback. Free tier: up to {FREE_TIER_LIMIT:,} customers.")
    st.markdown("---")
    st.markdown("### Step 1: Upload Files")
    uploaded_files = st.file_uploader("Drop files here",
        type=["csv","tsv","json","xlsx","xls","pdf","docx","txt"],
        accept_multiple_files=True, key="upload_tab_files")
    if not uploaded_files:
        st.info("Upload your customer data files to begin.")
        _show_formats()
        return False

    loaded_dfs = {}
    for f in uploaded_files:
        size_mb = f.size / 1024 / 1024
        if f.size > MAX_UPLOAD_BYTES:
            st.error(f"**{f.name}** is {size_mb:.1f} MB — max allowed is {MAX_UPLOAD_MB} MB. Split the file into smaller chunks and re-upload.")
            continue
        try:
            df, msg = read_file(f)
        except Exception as e:
            st.error(f"**{f.name}** — could not read file: {e}")
            continue
        if df is not None:
            loaded_dfs[f.name] = df
            st.success(f"**{f.name}** — {len(df):,} rows × {len(df.columns)} columns ({size_mb:.1f} MB)")
            if msg: st.caption(msg)
        else:
            st.error(f"**{f.name}** — {msg}")
    if not loaded_dfs: return False

    st.markdown("---")
    st.markdown("### Step 2: Identify Your Data")
    table_assignments = {}
    opts = ["— Skip —", "customer_master", "complaint_data", "interaction_data"]
    labels = {"customer_master": "Customer Profiles", "complaint_data": "Customer Feedback / Complaints", "interaction_data": "Service History / Interactions"}
    for fname, df in loaded_dfs.items():
        detected = auto_detect_table_type(df, fname)
        c1, c2 = st.columns([1, 2])
        with c1:
            assigned = st.selectbox(f"**{fname}**", opts,
                index=opts.index(detected) if detected in opts else 0, key=f"tt_{fname}")
        with c2:
            if assigned != "— Skip —":
                st.caption(f"→ {labels.get(assigned, assigned)}")
                st.caption(f"Columns: {', '.join(df.columns[:6])}")
        if assigned != "— Skip —":
            table_assignments[assigned] = fname
    if not table_assignments:
        st.warning("Please assign at least one file."); return False

    st.markdown("---")
    st.markdown("### Step 3: Match Columns")
    st.caption("We auto-matched your columns. Correct any mistakes below.")
    all_mappings = {}
    # Friendly column labels
    friendly = {
        "customer_id": "Customer ID", "customer_name": "Name", "age": "Age", "gender": "Gender",
        "region": "Region", "service_type": "Service Type", "contract_type": "Contract Type",
        "dwelling_type": "Property Type", "account_tenure_months": "Months as Customer",
        "has_autopay": "Auto-Pay", "paperless_billing": "Paperless Billing", "family_size": "Family Size",
        "income_bracket": "Income Level", "home_ownership": "Home Ownership",
        "comment": "Customer Comment/Feedback", "complaint_date": "Date", "complaint_category": "Category",
        "severity": "Severity/Rating", "escalated": "Escalated", "resolved": "Resolved",
        "resolution_time_days": "Resolution Days", "interaction_date": "Date", "interaction_type": "Type",
        "channel": "Channel", "duration_minutes": "Duration", "satisfaction_score": "Satisfaction Rating",
    }
    for tt, fname in table_assignments.items():
        df = loaded_dfs[fname]
        auto_map = auto_map_columns(df, tt)
        schema = EXPECTED_SCHEMAS[tt]
        st.markdown(f"#### {labels.get(tt, tt)} — `{fname}`")
        with st.expander(f"Preview {fname}", expanded=False):
            st.dataframe(df.head(5), use_container_width=True)
        all_exp = schema["required"] + schema["optional"]
        df_cols = ["— Not matched —"] + df.columns.tolist()
        mapping = {}
        cols = st.columns(3)
        for i, exp_col in enumerate(all_exp):
            is_req = exp_col in schema["required"]
            label = f"⚠️ {friendly.get(exp_col, exp_col)}" if is_req else friendly.get(exp_col, exp_col)
            auto = auto_map.get(exp_col)
            didx = df_cols.index(auto) if auto in df_cols else 0
            with cols[i % 3]:
                sel = st.selectbox(label, df_cols, index=didx, key=f"cm_{tt}_{exp_col}")
                if sel != "— Not matched —": mapping[exp_col] = sel
        missing = [friendly.get(r, r) for r in schema["required"] if r not in mapping]
        if missing: st.warning(f"Missing required: {', '.join(missing)}")
        else: st.success("✅ All required fields matched")
        all_mappings[tt] = mapping
        st.markdown("---")

    all_missing = []
    for tt, mapping in all_mappings.items():
        schema = EXPECTED_SCHEMAS[tt]
        for r in schema["required"]:
            if r not in mapping:
                all_missing.append(f"{labels.get(tt, tt)} → {friendly.get(r, r)}")

    st.markdown("### Step 4: Get Results")
    st.info(
        "Upload your customer data and our pre-trained model will score every customer instantly. "
        f"Pre-trained on 15,000 utility industry customers — no setup required."
    )

    if all_missing:
        st.error("Fix the missing required columns above before continuing:\n- " + "\n- ".join(all_missing))

    if st.button("🔮 Score My Customers", type="primary", use_container_width=True, disabled=bool(all_missing)):
        if not has_base:
            st.error("Base model not found. Please contact support."); return False
        result = _predict_only(loaded_dfs, table_assignments, all_mappings)
        return result

    st.markdown("---")
    st.markdown("#### 🔒 Custom Model Training *(Premium)*")
    st.markdown(
        "Train a model exclusively on your historical data for predictions tailored to your customer base. "
        "Requires your own labelled data (customers you know have churned or stayed)."
    )
    if st.button("🏗️ Train My Own Model", disabled=True, use_container_width=True,
                 help="Upgrade to a paid plan to unlock custom model training on your own historical data."):
        pass
    st.caption("Available on Professional and Enterprise plans. [Contact us to upgrade.](#)")

    # Re-render results from session state so download buttons survive reruns
    if st.session_state.get("prediction_results") is not None:
        st.markdown("---")
        st.markdown("### Results")
        _render_results(
            st.session_state.prediction_results,
            st.session_state.get("prediction_pdf"),
            st.session_state.get("prediction_xlsx"),
        )

    return False

def _get_dirs():
    """Return session-scoped dirs, falling back to global config paths."""
    from config import get_session_dirs
    sid = st.session_state.get("session_id")
    return get_session_dirs(sid) if sid else {}


def _history_file():
    dirs = _get_dirs()
    return os.path.join(dirs.get("data_dir", DATA_DIR), "run_history.json")


def _last_results_file():
    dirs = _get_dirs()
    return os.path.join(dirs.get("data_dir", DATA_DIR), "last_results.csv")


def _save_run_to_history(res):
    """Append a summary entry to this user's run_history.json."""
    import json
    from datetime import datetime
    entry = {
        "timestamp":      datetime.now().isoformat(),
        "total":          int(len(res)),
        "high_risk":      int((res["risk_level"] == "HIGH").sum()),
        "medium_risk":    int((res["risk_level"] == "MEDIUM").sum()),
        "low_risk":       int((res["risk_level"] == "LOW").sum()),
        "avg_churn_prob": round(float(res["churn_probability"].mean()), 4),
    }
    path = _history_file()
    try:
        history = json.loads(open(path).read()) if os.path.exists(path) else []
    except Exception:
        history = []
    history.insert(0, entry)          # newest first
    history = history[:20]            # keep last 20 runs
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        import json as _json
        _json.dump(history, f, indent=2)
    # Save the results CSV for re-download
    res.to_csv(_last_results_file(), index=False)


def restore_session_from_disk():
    """
    Called after login. If this user has previous results on disk, reload them
    into session state so their last run is immediately available.
    """
    if st.session_state.get("prediction_results") is not None:
        return  # already loaded this session

    last_csv = _last_results_file()
    if not os.path.exists(last_csv):
        return

    try:
        res = pd.read_csv(last_csv)
        if res.empty:
            return
        from src.report_generator import generate_pdf_report, generate_excel_report
        st.session_state.prediction_results = res
        st.session_state.prediction_pdf     = generate_pdf_report(res)
        try:
            st.session_state.prediction_xlsx = generate_excel_report(res)
        except RuntimeError:
            st.session_state.prediction_xlsx = None
    except Exception:
        pass

def _prepare_data(loaded_dfs, table_assignments, all_mappings, progress, status):
    dirs = _get_dirs()
    _data_dir = dirs.get("data_dir", DATA_DIR)
    os.makedirs(_data_dir, exist_ok=True)
    transformed = {}
    for tt, fname in table_assignments.items():
        df = loaded_dfs[fname]
        mapping = all_mappings.get(tt, {})
        transformed[tt] = transform_dataframe(df, mapping, tt)
        st.success(f"✅ {len(transformed[tt]):,} records processed")

    cids = None
    for tt in ["customer_master","complaint_data","interaction_data"]:
        if tt in transformed and "customer_id" in transformed[tt].columns:
            if cids is None: cids = transformed[tt]["customer_id"].unique().tolist()
    if cids is None:
        st.error("Could not find customer IDs in your data. Check column mapping."); return None, None, None, None

    # Check limit
    allowed, msg = check_data_limit(len(cids))
    if not allowed:
        render_upgrade_wall(len(cids))
        return None, None, None, None
    st.caption(f"✅ {len(cids):,} customers found")

    missing_tables = [tt for tt in EXPECTED_SCHEMAS if tt not in transformed]
    if missing_tables:
        friendly_names = {"customer_master": "Customer Profiles", "complaint_data": "Feedback / Complaints", "interaction_data": "Service Interactions"}
        missing_labels = [friendly_names.get(t, t) for t in missing_tables]
        st.warning(
            f"**Heads up:** You didn't upload {', '.join(missing_labels)}. "
            "The model will fill in placeholder values for these — predictions will be less accurate. "
            "For best results, upload all three file types."
        )
    for tt in EXPECTED_SCHEMAS:
        if tt not in transformed:
            transformed[tt] = generate_missing_data(tt, cids)
    if "customer_master" not in table_assignments:
        transformed["customer_master"] = generate_missing_data("customer_master", cids)

    fmap = {
        "customer_master":  dirs.get("customer_master_file",  CUSTOMER_MASTER_FILE),
        "complaint_data":   dirs.get("complaint_data_file",   COMPLAINT_DATA_FILE),
        "interaction_data": dirs.get("interaction_data_file", INTERACTION_DATA_FILE),
    }
    for tt, fp in fmap.items():
        transformed[tt].to_csv(fp, index=False)

    status.text("Analyzing your data...")
    from src.data_preprocessing import preprocess_pipeline
    from src.feature_engineering import engineer_features
    merged, features, ids, _ = preprocess_pipeline(dirs=dirs)
    engineered = engineer_features(merged, dirs=dirs)
    return transformed, merged, engineered, cids

def _predict_only(loaded_dfs, table_assignments, all_mappings):
    progress = st.progress(0); status = st.empty()
    status.text("Processing your data...")
    progress.progress(10)
    transformed, merged, engineered, cids = _prepare_data(loaded_dfs, table_assignments, all_mappings, progress, status)
    if engineered is None: return False
    progress.progress(50)

    status.text("Scoring your customers...")
    # Always use the permanent base model — never the demo/session model
    model    = joblib.load(os.path.join(BASE_MODEL_DIR, "best_model.pkl"))
    scaler   = joblib.load(os.path.join(BASE_MODEL_DIR, "scaler.pkl"))
    metadata = joblib.load(os.path.join(BASE_MODEL_DIR, "model_metadata.pkl"))
    progress.progress(60)

    trained_features = metadata.get("feature_names", [])
    label_encoders = metadata.get("label_encoders", {})
    drop_cols = ["customer_id","customer_name","account_start_date","most_common_complaint_category",TARGET_COLUMN]
    X = engineered.drop(columns=[c for c in drop_cols if c in engineered.columns], errors="ignore")
    for col in X.columns:
        if X[col].dtype == object:
            if col in label_encoders:
                le = label_encoders[col]; known = set(le.classes_)
                X[col] = X[col].astype(str).apply(lambda v: le.transform([v])[0] if v in known else 0)
            else:
                X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)
    X = X.fillna(0)
    for col in trained_features:
        if col not in X.columns: X[col] = 0
    X = X[[c for c in trained_features if c in X.columns]]
    X_scaled = scaler.transform(X)
    probs = model.predict_proba(X_scaled)[:, 1]
    preds = model.predict(X_scaled)
    progress.progress(85)

    res = engineered[["customer_id"]].copy() if "customer_id" in engineered.columns else pd.DataFrame({"customer_id": range(len(probs))})
    res["churn_probability"] = probs
    res["prediction"] = np.where(preds == 1, "At Risk", "Stable")
    res["risk_level"] = pd.cut(probs, bins=[0,0.4,0.7,1.0], labels=["LOW","MEDIUM","HIGH"])
    if "customer_master" in transformed:
        m = transformed["customer_master"]
        for col in ["customer_name","region","account_tenure_months","contract_type"]:
            if col in m.columns: res = res.merge(m[["customer_id",col]], on="customer_id", how="left")
    res = res.sort_values("churn_probability", ascending=False)
    progress.progress(100)

    status.text("✅ Complete!")
    st.balloons()

    # Persist results so download buttons survive reruns and come back on next login
    from src.report_generator import generate_pdf_report, generate_excel_report
    st.session_state.prediction_results = res
    st.session_state.prediction_pdf   = generate_pdf_report(res)
    try:
        st.session_state.prediction_xlsx = generate_excel_report(res)
    except RuntimeError:
        st.session_state.prediction_xlsx = None
    _save_run_to_history(res)

    # Generate EDA charts for uploaded data into a separate subdir
    try:
        from src.eda import generate_eda_report
        dirs = _get_dirs()
        upload_report_dir = os.path.join(dirs.get("report_dir", "reports"), "upload")
        os.makedirs(upload_report_dir, exist_ok=True)
        upload_eda_dirs = dict(dirs)
        upload_eda_dirs["report_dir"] = upload_report_dir
        generate_eda_report(merged, dirs=upload_eda_dirs)
    except Exception:
        pass

    # Build a predictor + chatbot on the uploaded data so all main tabs can use it
    try:
        dirs = _get_dirs()
        upload_dirs = dict(dirs)
        upload_dirs["model_dir"] = BASE_MODEL_DIR  # score using base model
        from src.prediction_engine import ChurnPredictor
        from src.chatbot import RetentionChatbot
        upload_predictor = ChurnPredictor(dirs=upload_dirs)
        upload_chatbot = RetentionChatbot(
            upload_predictor,
            nuro_key=st.session_state.get("nuro_api_key"),
            claude_key=st.session_state.get("claude_api_key"),
        )
        st.session_state.upload_predictor = upload_predictor
        st.session_state.upload_chatbot   = upload_chatbot
        st.session_state.active_view      = "upload"  # auto-switch main tabs to uploaded data
    except Exception:
        st.session_state.upload_predictor = None
        st.session_state.upload_chatbot   = None

    _render_results(res,
                    st.session_state.prediction_pdf,
                    st.session_state.prediction_xlsx)
    return True


def _render_results(res, pdf_bytes, xlsx_bytes):
    tab_summary, tab_lookup, tab_ai = st.tabs(["📊 Results Summary", "🔍 Customer Lookup", "🤖 Ask AI"])

    with tab_summary:
        n_h = (res["risk_level"]=="HIGH").sum()
        n_m = (res["risk_level"]=="MEDIUM").sum()
        n_l = (res["risk_level"]=="LOW").sum()
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("Total Customers", f"{len(res):,}")
        with c2: st.metric("🔴 High Risk", f"{n_h:,}")
        with c3: st.metric("🟡 Medium Risk", f"{n_m:,}")
        with c4: st.metric("🟢 Low Risk", f"{n_l:,}")

        st.markdown("#### Top At-Risk Customers")
        show_cols = [c for c in ["customer_id","customer_name","churn_probability","risk_level","prediction","region","account_tenure_months"] if c in res.columns]
        st.dataframe(res.head(20)[show_cols].style.format({"churn_probability":"{:.1%}"}), use_container_width=True)

        dl1, dl2, dl3 = st.columns(3)
        with dl1:
            st.download_button("📄 Download PDF Report", pdf_bytes,
                               "churn_report.pdf", "application/pdf", use_container_width=True)
        with dl2:
            if xlsx_bytes:
                st.download_button("📊 Download Excel Report", xlsx_bytes,
                                   "churn_report.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
            else:
                st.button("📊 Excel (install openpyxl)", disabled=True, use_container_width=True)
        with dl3:
            st.download_button("📥 Download CSV", res.to_csv(index=False),
                               "risk_scores.csv", "text/csv", use_container_width=True)

    with tab_lookup:
        predictor = st.session_state.get("upload_predictor")
        if predictor is None:
            st.warning("Customer lookup unavailable — predictor could not be loaded for this upload.")
        else:
            all_ids = res["customer_id"].tolist() if "customer_id" in res.columns else []
            cid = st.selectbox("Select a customer", ["— choose —"] + all_ids, key="upload_lookup_select")
            if cid and cid != "— choose —":
                result = predictor.predict_customer(cid)
                if "error" in result:
                    st.error(result["error"])
                else:
                    info = result.get("customer_info", {})
                    prob = result["churn_probability"]
                    risk = result["risk_level"]
                    color = "#e74c3c" if risk=="HIGH" else ("#f39c12" if risk=="MEDIUM" else "#27ae60")
                    st.markdown(f"### {info.get('name', cid)}")
                    st.markdown(f'<span style="background:{color};color:white;padding:4px 12px;border-radius:12px;font-weight:bold">{risk} RISK — {prob:.1%} churn probability</span>', unsafe_allow_html=True)
                    st.markdown("")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("Tenure", f"{info.get('tenure_months',0)} months")
                        st.metric("Region", info.get('region','N/A'))
                    with c2:
                        st.metric("Contract", info.get('contract_type','N/A'))
                        st.metric("Service", info.get('service_type','N/A'))
                    with c3:
                        st.metric("Complaints", info.get('complaint_count',0))
                        st.metric("Sentiment", f"{info.get('avg_sentiment_score',0):.2f}")

                    st.markdown("#### Recommended Actions")
                    recs = predictor.get_retention_recommendations(cid)
                    for r in recs.get("recommendations", []):
                        st.markdown(f"- {r}")

    with tab_ai:
        chatbot = st.session_state.get("upload_chatbot")
        if chatbot is None:
            st.warning("AI assistant unavailable for this upload.")
        else:
            st.caption(f"Ask anything about your uploaded customers. Powered by {chatbot.get_mode_label()}.")
            if "upload_chat_messages" not in st.session_state:
                st.session_state.upload_chat_messages = []
            for msg in st.session_state.upload_chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            prompt = st.chat_input("Ask about your uploaded data...", key="upload_chat_input")
            if prompt:
                st.session_state.upload_chat_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        response = chatbot.chat(prompt)
                    st.markdown(response)
                st.session_state.upload_chat_messages.append({"role": "assistant", "content": response})
            if st.session_state.upload_chat_messages:
                if st.button("🗑️ Clear chat", key="upload_clear_chat"):
                    st.session_state.upload_chat_messages = []
                    st.rerun()

def _retrain(loaded_dfs, table_assignments, all_mappings):
    dirs = _get_dirs()
    progress = st.progress(0); status = st.empty()
    status.text("Processing your data...")
    progress.progress(10)
    transformed, merged, engineered, cids = _prepare_data(loaded_dfs, table_assignments, all_mappings, progress, status)
    if engineered is None: return False
    progress.progress(40)

    n = len(cids) if cids else 0
    if n < 50:
        st.error(f"Only {n} customers. Full Analysis needs at least 50. Use Predict Only instead."); return False

    _cm_file = dirs.get("customer_master_file",  CUSTOMER_MASTER_FILE)
    _cd_file = dirs.get("complaint_data_file",   COMPLAINT_DATA_FILE)
    _id_file = dirs.get("interaction_data_file", INTERACTION_DATA_FILE)
    master = pd.read_csv(_cm_file)
    if "churned" not in master.columns or master["churned"].isna().all() or master["churned"].nunique() < 2:
        status.text("Analyzing customer behavior patterns...")
        master["churned"] = infer_churn_labels(master, pd.read_csv(_cd_file), pd.read_csv(_id_file))
        master.to_csv(_cm_file, index=False)
        from src.data_preprocessing import preprocess_pipeline
        from src.feature_engineering import engineer_features
        merged, _, _, _ = preprocess_pipeline(dirs=dirs)
        engineered = engineer_features(merged, dirs=dirs)
    progress.progress(55)

    status.text("Training custom models...")
    from src.model_training import training_pipeline
    from src.eda import generate_eda_report
    generate_eda_report(merged, dirs=dirs)
    try:
        results, trained_models, best_name, scaler, _ = training_pipeline(engineered, dirs=dirs)
    except ValueError as e:
        st.error(f"Cannot train model: {e}")
        return False
    st.session_state.models_trained = True
    st.session_state.training_results = results
    st.session_state.merged_data = merged
    progress.progress(90)

    from src.prediction_engine import ChurnPredictor
    from src.chatbot import RetentionChatbot
    predictor = ChurnPredictor(dirs=dirs)
    chatbot = RetentionChatbot(predictor)
    st.session_state.predictor = predictor
    st.session_state.chatbot = chatbot
    st.session_state.data_generated = True
    progress.progress(100)

    status.text("✅ Complete!")
    st.balloons()
    best_metrics = pd.DataFrame(results).T.loc[best_name]
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Accuracy", f"{best_metrics['accuracy']:.0%}")
    with c2: st.metric("Precision", f"{best_metrics['precision']:.0%}")
    with c3: st.metric("Detection Rate", f"{best_metrics['recall']:.0%}")
    st.success(f"Custom model trained on {n:,} of your customers. Check Dashboard and AI Assistant tabs.")
    return True

def _show_formats():
    with st.expander("📝 What can I upload?", expanded=False):
        st.markdown("""
**CSV with customer IDs and feedback:**
```
customer_id,feedback_text
C001,"Very frustrated with billing errors"
C002,"Thank you for the quick response"
```
**Also accepted:** Excel, JSON, PDF with tables, Word documents.
Column names don't need to match exactly — we'll auto-detect.
        """)

def render_sidebar_quick_upload():
    st.markdown("### 📂 Quick Upload")
    files = st.file_uploader("Upload files", type=["csv","tsv","json","xlsx","xls","pdf","docx","txt"],
        accept_multiple_files=True, key="sidebar_upload", label_visibility="collapsed")
    if files: st.caption(f"{len(files)} file(s) → go to Upload Data tab")
    return files
