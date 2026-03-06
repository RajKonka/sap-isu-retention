"""
Upload Tab UI — V3 (Hybrid: Predict Only + Optional Retrain)
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

def _base_model_exists():
    return (os.path.exists(os.path.join(MODEL_DIR, "best_model.pkl")) and
            os.path.exists(os.path.join(MODEL_DIR, "scaler.pkl")) and
            os.path.exists(os.path.join(MODEL_DIR, "model_metadata.pkl")))

def render_upload_tab():
    st.subheader("Upload Your Own Data")
    has_base = _base_model_exists()
    if has_base:
        st.markdown('<div style="background:#ecfdf5;border-left:4px solid #27ae60;padding:1rem;border-radius:0 8px 8px 0;margin-bottom:1rem;"><strong>Base model ready.</strong> Upload data and score customers instantly.</div>', unsafe_allow_html=True)
    else:
        st.warning("No base model found. Click Run Complete Pipeline first.")

    mode = st.radio("Pipeline Mode", ["Predict Only (recommended)", "Retrain on My Data"], index=0,
        help="Predict Only uses pre-trained base model. Retrain builds a new model on your data.")

    is_predict_only = "Predict Only" in mode
    if is_predict_only:
        st.info("Uses base model trained on 10,000 customers. Works with any dataset size.")
    else:
        st.info("Requires 100+ customers. Best with 500+ and churn labels.")

    st.markdown("---")
    st.markdown("### Step 1: Upload Files")
    uploaded_files = st.file_uploader("Drop files here",
        type=["csv","tsv","json","xlsx","xls","pdf","docx","txt"],
        accept_multiple_files=True, key="upload_tab_files")
    if not uploaded_files:
        st.info("Upload at least one file to begin.")
        return False

    loaded_dfs = {}
    for f in uploaded_files:
        df, msg = read_file(f)
        if df is not None:
            loaded_dfs[f.name] = df
            st.success(f"**{f.name}** — {len(df):,} rows x {len(df.columns)} cols")
            if msg: st.caption(msg)
        else:
            st.error(f"**{f.name}** — {msg}")
    if not loaded_dfs: return False

    st.markdown("---")
    st.markdown("### Step 2: Identify Data Sources")
    table_assignments = {}
    opts = ["— Skip —", "customer_master", "complaint_data", "interaction_data"]
    for fname, df in loaded_dfs.items():
        detected = auto_detect_table_type(df, fname)
        c1, c2 = st.columns([1, 2])
        with c1:
            assigned = st.selectbox(f"**{fname}**", opts,
                index=opts.index(detected) if detected in opts else 0, key=f"tt_{fname}")
        with c2:
            if assigned != "— Skip —":
                st.caption(f"{EXPECTED_SCHEMAS[assigned]['description']}")
                st.caption(f"Columns: {', '.join(df.columns[:6])}")
        if assigned != "— Skip —":
            table_assignments[assigned] = fname
    if not table_assignments:
        st.warning("Assign at least one file."); return False

    st.markdown("---")
    st.markdown("### Step 3: Map Columns")
    all_mappings = {}
    for tt, fname in table_assignments.items():
        df = loaded_dfs[fname]
        auto_map = auto_map_columns(df, tt)
        schema = EXPECTED_SCHEMAS[tt]
        st.markdown(f"#### {tt.replace('_',' ').title()} — `{fname}`")
        with st.expander(f"Preview {fname}", expanded=False):
            st.dataframe(df.head(5), use_container_width=True)
        all_exp = schema["required"] + schema["optional"]
        df_cols = ["— Not mapped —"] + df.columns.tolist()
        mapping = {}
        cols = st.columns(3)
        for i, exp_col in enumerate(all_exp):
            is_req = exp_col in schema["required"]
            label = f"⚠️ {exp_col}" if is_req else exp_col
            auto = auto_map.get(exp_col)
            didx = df_cols.index(auto) if auto in df_cols else 0
            with cols[i % 3]:
                sel = st.selectbox(label, df_cols, index=didx, key=f"cm_{tt}_{exp_col}")
                if sel != "— Not mapped —": mapping[exp_col] = sel
        missing = [r for r in schema["required"] if r not in mapping]
        if missing: st.warning(f"Missing required: {', '.join(missing)}")
        else: st.success("All required mapped")
        all_mappings[tt] = mapping
        st.markdown("---")

    st.markdown("### Step 4: Run")
    btn = "Score My Customers" if is_predict_only else "Retrain Model on My Data"
    if st.button(btn, type="primary", use_container_width=True):
        if is_predict_only:
            if not has_base:
                st.error("No base model. Run Complete Pipeline first."); return False
            return _predict_only(loaded_dfs, table_assignments, all_mappings)
        else:
            return _retrain(loaded_dfs, table_assignments, all_mappings)
    return False

def _prepare_uploaded_data(loaded_dfs, table_assignments, all_mappings, progress, status):
    os.makedirs(DATA_DIR, exist_ok=True)
    transformed = {}
    for tt, fname in table_assignments.items():
        df = loaded_dfs[fname]
        mapping = all_mappings.get(tt, {})
        transformed[tt] = transform_dataframe(df, mapping, tt)
        st.success(f"{tt}: {len(transformed[tt]):,} rows")

    cids = None
    for tt in ["customer_master","complaint_data","interaction_data"]:
        if tt in transformed and "customer_id" in transformed[tt].columns:
            if cids is None: cids = transformed[tt]["customer_id"].unique().tolist()
    if cids is None:
        st.error("No customer_id found."); return None, None, None

    for tt in EXPECTED_SCHEMAS:
        if tt not in transformed:
            transformed[tt] = generate_missing_data(tt, cids)
    if "customer_master" not in table_assignments:
        transformed["customer_master"] = generate_missing_data("customer_master", cids)

    fmap = {"customer_master": CUSTOMER_MASTER_FILE, "complaint_data": COMPLAINT_DATA_FILE, "interaction_data": INTERACTION_DATA_FILE}
    for tt, fp in fmap.items():
        transformed[tt].to_csv(fp, index=False)

    status.text("Running NLP sentiment analysis...")
    from src.data_preprocessing import preprocess_pipeline
    from src.feature_engineering import engineer_features
    merged, features, ids, _ = preprocess_pipeline()
    engineered = engineer_features(merged)
    return transformed, merged, engineered

def _predict_only(loaded_dfs, table_assignments, all_mappings):
    progress = st.progress(0); status = st.empty()
    status.text("Transforming data...")
    progress.progress(10)
    transformed, merged, engineered = _prepare_uploaded_data(loaded_dfs, table_assignments, all_mappings, progress, status)
    if engineered is None: return False
    progress.progress(50)

    status.text("Loading base model...")
    model = joblib.load(os.path.join(MODEL_DIR, "best_model.pkl"))
    scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
    metadata = joblib.load(os.path.join(MODEL_DIR, "model_metadata.pkl"))
    progress.progress(60)

    status.text("Scoring customers...")
    trained_features = metadata.get("feature_names", [])
    label_encoders = metadata.get("label_encoders", {})
    drop_cols = ["customer_id","customer_name","account_start_date","most_common_complaint_category",TARGET_COLUMN]
    X = engineered.drop(columns=[c for c in drop_cols if c in engineered.columns], errors="ignore")
    for col in X.columns:
        if X[col].dtype == object:
            if col in label_encoders:
                le = label_encoders[col]
                known = set(le.classes_)
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
    res["prediction"] = np.where(preds == 1, "Will Churn", "Will Stay")
    res["risk_level"] = pd.cut(probs, bins=[0,0.4,0.7,1.0], labels=["LOW","MEDIUM","HIGH"])
    if "customer_master" in transformed:
        m = transformed["customer_master"]
        for col in ["customer_name","region","account_tenure_months","contract_type"]:
            if col in m.columns: res = res.merge(m[["customer_id",col]], on="customer_id", how="left")
    res = res.sort_values("churn_probability", ascending=False)
    progress.progress(100)

    status.text("Done!")
    st.balloons()
    n_h = (res["risk_level"]=="HIGH").sum()
    n_m = (res["risk_level"]=="MEDIUM").sum()
    n_l = (res["risk_level"]=="LOW").sum()
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Total", f"{len(res):,}")
    with c2: st.metric("High Risk", f"{n_h:,}")
    with c3: st.metric("Medium Risk", f"{n_m:,}")
    with c4: st.metric("Low Risk", f"{n_l:,}")

    st.markdown("### Top At-Risk Customers")
    show_cols = [c for c in ["customer_id","churn_probability","risk_level","prediction","customer_name","region","account_tenure_months"] if c in res.columns]
    st.dataframe(res.head(20)[show_cols].style.format({"churn_probability":"{:.1%}"}), use_container_width=True)
    st.download_button("Download Full Results (CSV)", res.to_csv(index=False), "churn_predictions.csv", "text/csv", use_container_width=True)
    return True

def _retrain(loaded_dfs, table_assignments, all_mappings):
    progress = st.progress(0); status = st.empty()
    status.text("Transforming data...")
    progress.progress(10)
    transformed, merged, engineered = _prepare_uploaded_data(loaded_dfs, table_assignments, all_mappings, progress, status)
    if engineered is None: return False
    progress.progress(40)

    cids = None
    for tt in transformed:
        if "customer_id" in transformed[tt].columns:
            cids = transformed[tt]["customer_id"].unique().tolist(); break
    n = len(cids) if cids else 0
    if n < 50:
        st.error(f"Only {n} customers. Retrain needs 50+. Use Predict Only instead."); return False

    master = pd.read_csv(CUSTOMER_MASTER_FILE)
    if "churned" not in master.columns or master["churned"].isna().all() or master["churned"].nunique() < 2:
        status.text("Inferring churn labels...")
        master["churned"] = infer_churn_labels(master, pd.read_csv(COMPLAINT_DATA_FILE), pd.read_csv(INTERACTION_DATA_FILE))
        master.to_csv(CUSTOMER_MASTER_FILE, index=False)
        st.info(f"Churn labels inferred ({master['churned'].mean():.1%} churn rate)")
        # Re-run preprocessing with labels
        from src.data_preprocessing import preprocess_pipeline
        from src.feature_engineering import engineer_features
        merged, _, _, _ = preprocess_pipeline()
        engineered = engineer_features(merged)
    progress.progress(55)

    status.text("Training models...")
    from src.model_training import training_pipeline
    from src.eda import generate_eda_report
    generate_eda_report(merged)
    results, trained_models, best_name, scaler = training_pipeline(engineered)
    st.session_state.models_trained = True
    st.session_state.training_results = results
    st.session_state.merged_data = merged
    progress.progress(90)

    from src.prediction_engine import ChurnPredictor
    from src.chatbot import RetentionChatbot
    predictor = ChurnPredictor()
    chatbot = RetentionChatbot(predictor)
    st.session_state.predictor = predictor
    st.session_state.chatbot = chatbot
    st.session_state.data_generated = True
    progress.progress(100)

    status.text("Done!")
    st.balloons()
    st.dataframe(pd.DataFrame(results).T.style.format("{:.4f}").highlight_max(axis=0, color="#90EE90"), use_container_width=True)
    st.success(f"Best model: **{best_name}** — trained on {n:,} customers")
    return True

def render_sidebar_quick_upload():
    st.markdown("### Quick Upload")
    files = st.file_uploader("Upload files", type=["csv","tsv","json","xlsx","xls","pdf","docx","txt"],
        accept_multiple_files=True, key="sidebar_upload", label_visibility="collapsed")
    if files: st.caption(f"{len(files)} file(s) → go to Upload Data tab")
    return files
