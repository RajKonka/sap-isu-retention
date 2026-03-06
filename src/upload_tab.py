"""
Upload Tab UI — V3
Renders the data upload interface in the app.
Import this in app.py and call render_upload_tab()
"""
import streamlit as st
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *
from src.data_upload import (
    read_file, auto_detect_table_type, auto_map_columns,
    transform_dataframe, generate_missing_data, infer_churn_labels,
    EXPECTED_SCHEMAS, COLUMN_ALIASES,
)


def render_upload_tab():
    """Render the full data upload tab."""
    st.subheader("📂 Upload Your Own Data")

    st.markdown("""
    <div style="background: #f0f4ff; border-left: 4px solid #667eea; padding: 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <strong>Supported formats:</strong> CSV, TSV, JSON, Excel (.xlsx/.xls), PDF (with tables), Word (.docx), TXT<br>
        <strong>Minimum requirement:</strong> At least one file with a customer ID column and complaint/feedback text.<br>
        <strong>Auto-detection:</strong> We'll automatically detect which columns map to our pipeline. You can correct any mistakes before running.
    </div>
    """, unsafe_allow_html=True)

    # ── Step 1: Upload Files ──
    st.markdown("### Step 1: Upload Your Files")
    st.caption("Upload 1-3 files. We need at minimum a customer list and complaint/feedback data.")

    uploaded_files = st.file_uploader(
        "Drop files here",
        type=["csv", "tsv", "json", "xlsx", "xls", "pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="upload_tab_files",
    )

    if not uploaded_files:
        st.info("Upload at least one file to begin. We'll auto-detect the format and column structure.")
        _show_example_formats()
        return False

    # ── Read all files ──
    loaded_dfs = {}
    for f in uploaded_files:
        df, message = read_file(f)
        if df is not None:
            loaded_dfs[f.name] = df
            st.success(f"✅ **{f.name}** — {len(df):,} rows × {len(df.columns)} columns")
            if message:
                st.caption(message)
        else:
            st.error(f"❌ **{f.name}** — {message}")

    if not loaded_dfs:
        return False

    st.markdown("---")

    # ── Step 2: Auto-detect table types ──
    st.markdown("### Step 2: Identify Data Sources")
    st.caption("We detected which pipeline input each file maps to. Correct if needed.")

    table_assignments = {}
    table_options = ["— Skip this file —", "customer_master", "complaint_data", "interaction_data"]

    for filename, df in loaded_dfs.items():
        detected = auto_detect_table_type(df, filename)
        col1, col2 = st.columns([1, 2])
        with col1:
            assigned = st.selectbox(
                f"**{filename}**",
                table_options,
                index=table_options.index(detected) if detected in table_options else 0,
                key=f"table_type_{filename}",
            )
        with col2:
            if assigned != "— Skip this file —":
                schema = EXPECTED_SCHEMAS[assigned]
                st.caption(f"→ {schema['description']}")
                st.caption(f"Columns found: {', '.join(df.columns[:8])}{'...' if len(df.columns) > 8 else ''}")

        if assigned != "— Skip this file —":
            table_assignments[assigned] = filename

    if not table_assignments:
        st.warning("Please assign at least one file to continue.")
        return False

    st.markdown("---")

    # ── Step 3: Column Mapping ──
    st.markdown("### Step 3: Map Columns")
    st.caption("We auto-matched your columns to our pipeline. Green = confident match. Correct any mistakes.")

    all_mappings = {}
    for table_type, filename in table_assignments.items():
        df = loaded_dfs[filename]
        auto_mapping = auto_map_columns(df, table_type)

        st.markdown(f"#### {table_type.replace('_', ' ').title()} — `{filename}`")

        with st.expander(f"Preview: {filename}", expanded=False):
            st.dataframe(df.head(5), use_container_width=True)

        schema = EXPECTED_SCHEMAS[table_type]
        all_expected = schema["required"] + schema["optional"]
        df_cols = ["— Not mapped —"] + df.columns.tolist()

        mapping = {}
        cols = st.columns(3)
        for i, expected_col in enumerate(all_expected):
            is_required = expected_col in schema["required"]
            label = f"⚠️ {expected_col}" if is_required else expected_col

            # Find auto-detected match
            auto_match = auto_mapping.get(expected_col, None)
            default_idx = df_cols.index(auto_match) if auto_match in df_cols else 0

            with cols[i % 3]:
                selected = st.selectbox(
                    label,
                    df_cols,
                    index=default_idx,
                    key=f"colmap_{table_type}_{expected_col}",
                )
                if selected != "— Not mapped —":
                    mapping[expected_col] = selected

        # Validate required
        missing = [r for r in schema["required"] if r not in mapping]
        if missing:
            st.warning(f"⚠️ Missing required: {', '.join(missing)}")
        else:
            st.success(f"✅ All required columns mapped")

        all_mappings[table_type] = mapping
        st.markdown("---")

    # ── Step 4: Transform & Run ──
    st.markdown("### Step 4: Transform & Load")

    if st.button("🚀 Transform Data & Run Pipeline", type="primary", use_container_width=True):
        return _execute_upload_pipeline(loaded_dfs, table_assignments, all_mappings)

    return False


def render_sidebar_quick_upload():
    """Render a compact upload widget in the sidebar."""
    st.markdown("### 📂 Quick Upload")
    files = st.file_uploader(
        "Upload data files",
        type=["csv", "tsv", "json", "xlsx", "xls", "pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="sidebar_upload",
        label_visibility="collapsed",
    )
    if files:
        st.caption(f"{len(files)} file(s) ready")
        st.caption("Go to 📂 Upload Data tab to map columns")
        # Store for the tab to use
        st.session_state._sidebar_files = files
    return files


def _execute_upload_pipeline(loaded_dfs, table_assignments, all_mappings):
    """Transform uploaded data and run through the pipeline."""
    progress = st.progress(0)
    status = st.empty()

    os.makedirs(DATA_DIR, exist_ok=True)

    # ── Transform each assigned table ──
    transformed_tables = {}
    for table_type, filename in table_assignments.items():
        status.text(f"Transforming {table_type}...")
        df = loaded_dfs[filename]
        mapping = all_mappings.get(table_type, {})
        transformed = transform_dataframe(df, mapping, table_type)
        transformed_tables[table_type] = transformed
        st.success(f"✅ {table_type}: {len(transformed):,} rows, {len(transformed.columns)} columns")
    progress.progress(30)

    # ── Get customer IDs ──
    customer_ids = None
    if "customer_master" in transformed_tables:
        customer_ids = transformed_tables["customer_master"]["customer_id"].tolist()
    else:
        # Try to extract from any available table
        for tt, df in transformed_tables.items():
            if "customer_id" in df.columns:
                customer_ids = df["customer_id"].unique().tolist()
                break

    if customer_ids is None:
        st.error("❌ No customer_id column found in any file. Cannot proceed.")
        return False

    # ── Generate missing tables ──
    status.text("Generating placeholder data for missing inputs...")
    for table_type in EXPECTED_SCHEMAS:
        if table_type not in transformed_tables:
            placeholder = generate_missing_data(table_type, customer_ids)
            transformed_tables[table_type] = placeholder
            st.info(f"ℹ️ Generated placeholder for {table_type} (not uploaded)")
    progress.progress(50)

    # ── Generate customer master if missing ──
    if "customer_master" not in table_assignments:
        master = transformed_tables["customer_master"]
    else:
        master = transformed_tables["customer_master"]

    # ── Add churn labels if not present ──
    if "churned" not in master.columns or master["churned"].isna().all():
        status.text("Inferring churn labels from behavioral patterns...")
        master["churned"] = infer_churn_labels(
            master,
            transformed_tables.get("complaint_data", pd.DataFrame()),
            transformed_tables.get("interaction_data", pd.DataFrame()),
        )
        churn_rate = master["churned"].mean()
        st.info(f"ℹ️ Churn labels inferred from behavior (rate: {churn_rate:.1%})")
    progress.progress(60)

    # ── Save all files ──
    status.text("Saving transformed data...")
    file_map = {
        "customer_master": CUSTOMER_MASTER_FILE,
        "complaint_data": COMPLAINT_DATA_FILE,
        "interaction_data": INTERACTION_DATA_FILE,
    }
    for table_type, filepath in file_map.items():
        transformed_tables[table_type].to_csv(filepath, index=False)

    progress.progress(70)

    # ── Run the preprocessing + training pipeline ──
    status.text("Running NLP sentiment analysis...")
    from src.data_preprocessing import preprocess_pipeline
    merged, features, ids, _ = preprocess_pipeline()
    progress.progress(80)

    status.text("Engineering features...")
    from src.feature_engineering import engineer_features
    from src.eda import generate_eda_report
    generate_eda_report(merged)
    engineered = engineer_features(merged)
    st.session_state.merged_data = merged
    progress.progress(85)

    status.text("Training ML models...")
    from src.model_training import training_pipeline
    results, trained_models, best_name, scaler = training_pipeline(engineered)
    st.session_state.models_trained = True
    st.session_state.training_results = results
    progress.progress(95)

    status.text("Loading prediction engine...")
    from src.prediction_engine import ChurnPredictor
    from src.chatbot import RetentionChatbot
    predictor = ChurnPredictor()
    chatbot = RetentionChatbot(predictor)
    st.session_state.predictor = predictor
    st.session_state.chatbot = chatbot
    st.session_state.data_generated = True
    progress.progress(100)

    status.text("✅ Complete!")
    st.success(f"🎉 Pipeline complete on your data! Best model: **{best_name}**")
    st.balloons()

    return True


def _show_example_formats():
    """Show example data formats the user can upload."""
    with st.expander("📝 Example formats we accept", expanded=False):
        st.markdown("""
**Minimum viable upload — just 1 CSV with customer ID + comments:**
```
customer_id,feedback_text
C001,"Very frustrated with the billing errors on my account"
C002,"Thank you for the quick response to my query"
C003,"I want to cancel, nobody has called me back"
```

**More complete — separate files for customers and complaints:**

*customers.xlsx:*
| id | name | tenure_months | contract |
|------|-------|---------------|----------|
| C001 | Alice | 6 | Prepaid |
| C002 | Bob | 48 | Residential |

*tickets.csv:*
| account_id | issue_text | severity | date |
|------|------|------|------|
| C001 | "Bill is wrong again" | 4 | 2024-08-15 |
| C001 | "Still not fixed!" | 5 | 2024-09-01 |

**We also accept:** JSON, PDF with tables, Word documents with tables, tab-separated text files.

Column names don't need to match exactly — we'll auto-detect and let you correct.
        """)
