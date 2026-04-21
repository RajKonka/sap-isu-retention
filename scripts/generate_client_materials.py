"""
Generates 4 professional documents for Vantive Inc.:
  1. Internal Technical Reference (PDF)
  2. Client Sales Brief (PDF)
  3. Internal Technical Deck (PPTX)
  4. Client Presentation — STAR method (PPTX)
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# ── Output ────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "client_materials")
os.makedirs(OUT, exist_ok=True)

# ── Brand Palette ─────────────────────────────────────────────
NAVY   = colors.HexColor("#0D2137")
BLUE   = colors.HexColor("#1565C0")
CYAN   = colors.HexColor("#00B4D8")
ORANGE = colors.HexColor("#F4A300")
GREEN  = colors.HexColor("#2E7D32")
RED    = colors.HexColor("#C62828")
LIGHT  = colors.HexColor("#EEF2F7")
GREY   = colors.HexColor("#546E7A")
WHITE  = colors.white
BLACK  = colors.black

# PPT RGB versions
def rgb(h): r=int(h[1:3],16); g=int(h[3:5],16); b=int(h[5:7],16); return RGBColor(r,g,b)
NAVY_R=rgb("#0D2137"); BLUE_R=rgb("#1565C0"); CYAN_R=rgb("#00B4D8")
ORANGE_R=rgb("#F4A300"); GREEN_R=rgb("#2E7D32"); RED_R=rgb("#C62828")
LIGHT_R=rgb("#EEF2F7"); GREY_R=rgb("#546E7A"); WHITE_R=RGBColor(255,255,255)
DARK_R=rgb("#060F1A"); MID_R=rgb("#0A1A2E")

W, H = 13.33, 7.5   # slide dimensions in inches


# ═══════════════════════════════════════════════════════════════
#  SHARED PDF HELPERS
# ═══════════════════════════════════════════════════════════════

def base_styles():
    s = {}
    def P(name, **kw): s[name] = ParagraphStyle(name, **kw); return s[name]
    P("h1",    fontSize=20, textColor=NAVY,   leading=26, spaceBefore=20, spaceAfter=6,  fontName="Helvetica-Bold")
    P("h2",    fontSize=14, textColor=BLUE,   leading=20, spaceBefore=14, spaceAfter=4,  fontName="Helvetica-Bold")
    P("h3",    fontSize=11, textColor=BLUE,   leading=16, spaceBefore=10, spaceAfter=3,  fontName="Helvetica-Bold")
    P("body",  fontSize=10, textColor=BLACK,  leading=16, spaceAfter=6,   fontName="Helvetica", alignment=TA_JUSTIFY)
    P("bullet",fontSize=10, textColor=BLACK,  leading=15, spaceAfter=4,   fontName="Helvetica", leftIndent=16, bulletIndent=4)
    P("code",  fontSize=9,  textColor=colors.HexColor("#1A237E"), leading=14, spaceAfter=4,
               fontName="Courier", leftIndent=20, backColor=LIGHT)
    P("note",  fontSize=9,  textColor=GREY,   leading=13, spaceAfter=4,   fontName="Helvetica-Oblique", alignment=TA_JUSTIFY)
    P("center",fontSize=10, textColor=BLACK,  leading=15, spaceAfter=6,   fontName="Helvetica", alignment=TA_CENTER)
    P("footer",fontSize=8,  textColor=GREY,   leading=12, fontName="Helvetica", alignment=TA_CENTER)
    P("tag",   fontSize=9,  textColor=WHITE,  leading=13, fontName="Helvetica-Bold", alignment=TA_CENTER)
    P("kpi_num",fontSize=28,textColor=ORANGE, leading=34, fontName="Helvetica-Bold", alignment=TA_CENTER)
    P("kpi_lbl",fontSize=9, textColor=GREY,   leading=13, fontName="Helvetica",     alignment=TA_CENTER)
    return s

def cover_band(text, bg, fg, doc_width=16.6):
    tbl = Table([[Paragraph(text, ParagraphStyle("x", fontSize=11 if "©" in text else 13,
                  textColor=fg, fontName="Helvetica-Bold" if "©" not in text else "Helvetica",
                  alignment=TA_CENTER, leading=18))]],
                colWidths=[doc_width*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),bg),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
    ]))
    return tbl

def section_rule(story, s):
    story.append(HRFlowable(width="100%", thickness=2, color=CYAN, spaceAfter=8))

def info_table(data, col_widths, header_bg=NAVY, alt=True):
    style = [
        ("BACKGROUND",   (0,0),(-1,0), header_bg),
        ("TEXTCOLOR",    (0,0),(-1,0), WHITE),
        ("FONTNAME",     (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0),(-1,-1),9),
        ("GRID",         (0,0),(-1,-1),0.5,colors.HexColor("#CFD8DC")),
        ("TOPPADDING",   (0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",  (0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("VALIGN",       (0,0),(-1,-1),"TOP"),
    ]
    if alt:
        for i in range(1, len(data)):
            bg = LIGHT if i % 2 == 1 else WHITE
            style.append(("BACKGROUND",(0,i),(-1,i),bg))
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(style))
    return t


# ═══════════════════════════════════════════════════════════════
#  PDF 1 — INTERNAL TECHNICAL REFERENCE
# ═══════════════════════════════════════════════════════════════

def build_internal_pdf():
    path = os.path.join(OUT, "Vantive_Internal_Technical_Reference.pdf")
    doc  = SimpleDocTemplate(path, pagesize=A4,
           leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.2*cm, bottomMargin=2.2*cm)
    s    = base_styles()
    story= []

    # Cover
    title_tbl = Table([[Paragraph(
        "SAP IS-U Customer Retention System<br/>INTERNAL TECHNICAL REFERENCE",
        ParagraphStyle("ct",fontSize=22,textColor=WHITE,leading=30,
                       fontName="Helvetica-Bold",alignment=TA_CENTER)
    )]], colWidths=[16.6*cm])
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY),
        ("TOPPADDING",(0,0),(-1,-1),40),("BOTTOMPADDING",(0,0),(-1,-1),40),
    ]))
    story.append(title_tbl); story.append(Spacer(1,0.3*cm))
    story.append(cover_band("Vantive Inc.  ·  Version 3.0  ·  2026  ·  CONFIDENTIAL — INTERNAL USE ONLY", BLUE, WHITE))
    story.append(Spacer(1,0.3*cm))
    story.append(cover_band("raj.konka@vantiveinc.com  ·  konkarajkumar12@gmail.com", NAVY, CYAN))
    story.append(Spacer(1,1.0*cm))

    # TOC
    story.append(Paragraph("Table of Contents", s["h1"]))
    section_rule(story, s)
    toc = [
        ("1", "System Architecture & Tech Stack"),
        ("2", "File Structure & Module Responsibilities"),
        ("3", "Full Data Pipeline — Step by Step"),
        ("4", "Feature Engineering — All 50 Signals"),
        ("5", "Machine Learning Model — Training & Inference"),
        ("6", "NuroStudio AI Assistant — Architecture"),
        ("7", "Session Isolation & Multi-User Architecture"),
        ("8", "Registration, Auth & Security"),
        ("9", "Base Model — Training Protocol"),
        ("10","Validation Metrics & Acceptance Criteria"),
        ("11","Deployment & Infrastructure Notes"),
        ("12","Known Limitations & Roadmap"),
    ]
    for num, title in toc:
        story.append(Paragraph(f"  {num}.   {title}", s["body"]))
    story.append(PageBreak())

    # ── Section 1: Architecture ──
    story.append(Paragraph("1. System Architecture & Tech Stack", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph(
        "The system is a multi-tab Streamlit web application backed by a scikit-learn / LightGBM "
        "ensemble ML pipeline. It runs as a single-process Python application with per-user session "
        "isolation via UUID-keyed file directories. All state is file-backed (no database).", s["body"]))
    arch = [
        ["Layer", "Technology", "Purpose"],
        ["Frontend", "Streamlit ≥ 1.30", "UI, session state, tab routing"],
        ["ML Core", "scikit-learn, LightGBM, joblib", "Model training, serialisation, inference"],
        ["NLP", "VADER (NLTK)", "Sentiment analysis on complaint text"],
        ["Data I/O", "pandas, openpyxl, PyMuPDF, python-docx", "CSV / Excel / PDF / Word ingestion"],
        ["Reports", "matplotlib (PdfPages), openpyxl", "Multi-page PDF + 4-sheet XLSX export"],
        ["AI Assistant", "NuroStudio API → Claude API (Anthropic)", "Conversational AI with domain context"],
        ["Auth", "PBKDF2-SHA256, 260k iterations, compare_digest", "Password hashing, timing-safe comparison"],
        ["File Locking", "fcntl (POSIX)", "Concurrent-safe JSON writes for multi-user"],
        ["Storage", "Local filesystem (gitignored paths)", "Session data, models, reports"],
    ]
    story.append(info_table(arch, [3.0*cm, 5.5*cm, 8.1*cm]))
    story.append(Spacer(1,0.5*cm))

    # ── Section 2: File Structure ──
    story.append(Paragraph("2. File Structure & Module Responsibilities", s["h1"]))
    section_rule(story, s)
    files = [
        ["File / Path", "Responsibility"],
        ["app.py", "Entry point. 5 tabs. Injects CSS. Manages sidebar demo button and session_dirs."],
        ["config.py", "All global constants: DATA_DIR, MODEL_DIR, FREE_TIER_LIMIT, get_session_dirs(id)"],
        ["src/registration.py", "Register + sign-in forms. PBKDF2 hash. fcntl locking. Accounts + leads → storage/"],
        ["src/upload_tab.py", "Upload UI. Auto mode detection. _predict_only, _retrain, _render_results, _render_history, restore_session_from_disk"],
        ["src/data_upload.py", "File reading (CSV/Excel/PDF/Word/JSON). Fuzzy column mapping ≥0.75. Table type detection. infer_churn_labels."],
        ["src/data_preprocessing.py", "Cleans + merges 3 CSVs. VADER NLP on complaint comments. preprocess_pipeline(dirs=None)."],
        ["src/feature_engineering.py", "50 features: engagement_score, 8 risk flags, composite_risk_score. engineer_features(df, dirs=None)."],
        ["src/model_training.py", "Trains LR, RF, GBM, LightGBM, Ensemble. Picks best by ROC AUC. training_pipeline(df, dirs=None)."],
        ["src/prediction_engine.py", "ChurnPredictor class. predict_customer, get_top_risk_customers, get_segment_analysis."],
        ["src/data_generator.py", "Generates synthetic 5k demo customers. Severity-based comments (NOT churn-based)."],
        ["src/chatbot.py", "NuroStudio → Claude API → fallback. MAX_INPUT_CHARS=5000. 50-message history cap."],
        ["src/report_generator.py", "generate_pdf_report(res_df) multi-page PDF. generate_excel_report(res_df) 4-sheet XLSX."],
        ["src/eda.py", "8 EDA charts saved to session reports dir."],
        ["scripts/train_base_model.py", "Trains base model on 15,000 synthetic customers. Saves to models/base/."],
        ["models/base/", "COMMITTED to git. 8 pkl files. Ensemble, ROC AUC 0.828, 80% acc, 23% churn rate."],
        ["storage/accounts.json", "GITIGNORED. Registered user records with hashed passwords and permanent session_id."],
        ["storage/leads.json", "GITIGNORED. Lead capture (name, email, company, phone) from registration form."],
        ["data/sessions/{uuid}/", "GITIGNORED. Per-user runtime data: merged CSVs, features, run_history.json, last_results.csv."],
        ["models/sessions/{uuid}/", "GITIGNORED. Per-user trained models from Full Analysis mode."],
        ["sample_data/", "COMMITTED. 3 test datasets × 3 files (master, complaints, interactions)."],
    ]
    story.append(info_table(files, [5.0*cm, 11.6*cm]))
    story.append(PageBreak())

    # ── Section 3: Full Pipeline ──
    story.append(Paragraph("3. Full Data Pipeline — Step by Step", s["h1"]))
    section_rule(story, s)

    story.append(Paragraph("3.1  Predict Only Mode (no churned column in data)", s["h2"]))
    story.append(Paragraph(
        "Triggered when uploaded data does NOT contain a 'churned' column with 2+ distinct classes. "
        "Uses the pre-trained base model in models/base/. Never overwrites the base model.", s["body"]))
    steps_predict = [
        ("File Upload", "data_upload.py", "User uploads CSV/Excel/JSON/PDF/Word. Files read into pandas DataFrames."),
        ("Column Mapping", "data_upload.py", "Fuzzy string matching (threshold ≥ 0.75) maps user column names to canonical schema. "
         "E.g. 'cust_id' → 'customer_id', 'tenure_months' → 'account_tenure_months'."),
        ("Table Classification", "data_upload.py", "System detects whether file is customer_master, complaints, or interactions "
         "based on column signature. Multi-file upload merges all three."),
        ("Churn Label Inference", "data_upload.py", "If no churned col: infer_churn_labels() computes risk score from "
         "complaint_count, avg_severity, avg_satisfaction. Sigmoid(threshold=0.45) → binary label."),
        ("Preprocessing", "data_preprocessing.py", "Merge master + complaints + interactions on customer_id. Handle missing values. "
         "Group complaint records: complaint_count, avg_severity, unresolved_complaints. "
         "Group interaction records: total_interactions, avg_satisfaction_score, interactions_per_month."),
        ("VADER NLP", "data_preprocessing.py", "SentimentIntensityAnalyzer().polarity_scores(comment)['compound'] for every "
         "complaint comment. Aggregate per customer: avg_sentiment_score, negative_sentiment_ratio, sentiment_std."),
        ("Feature Engineering", "feature_engineering.py", "Compute engagement_score (weighted sum), 8 binary risk flags "
         "(each with specific thresholds), composite_risk_score (sum of flags). Total: ~50 features."),
        ("Base Model Load", "upload_tab.py", "_base_model_exists() checks models/base/. Auto-restores via "
         "'git restore models/base/' if missing. Loads best_model.pkl, scaler.pkl, model_metadata.pkl."),
        ("Scaling + Inference", "prediction_engine.py", "scaler.transform(X). model.predict_proba(X)[:,1] → churn probability per customer."),
        ("Risk Tier Assignment", "prediction_engine.py", "prob ≥ 0.70 → High. 0.40–0.69 → Medium. < 0.40 → Low."),
        ("Results Render", "upload_tab.py", "_render_results(): sorted DataFrame by probability desc. 3 download buttons "
         "(PDF, Excel, CSV). Results stored in st.session_state."),
        ("History Save", "upload_tab.py", "_save_run_to_history(): appends to run_history.json + last_results.csv in session dir."),
    ]
    for step, module, desc in steps_predict:
        story.append(Paragraph(f"<b>{step}</b>  <i>({module})</i>", s["h3"]))
        story.append(Paragraph(desc, s["body"]))

    story.append(Paragraph("3.2  Full Analysis Mode (has churned column)", s["h2"]))
    story.append(Paragraph(
        "Triggered when uploaded data contains a 'churned' column with at least 2 distinct classes (0 and 1). "
        "Trains a custom model in models/sessions/{uuid}/ from the user's real historical data.", s["body"]))
    story.append(Paragraph(
        "Steps 1–7 are identical to Predict Only. After feature engineering:", s["body"]))
    steps_retrain = [
        ("Train/Test Split", "model_training.py", "80/20 stratified split on the churned column."),
        ("Model Training", "model_training.py", "Trains: LogisticRegression, RandomForestClassifier (300 trees), "
         "GradientBoostingClassifier, LGBMClassifier, VotingClassifier (soft, equal weights). "
         "StandardScaler fitted on training set only."),
        ("Model Selection", "model_training.py", "Each model evaluated by ROC AUC on test set. Best single model + "
         "ensemble both saved. Metadata (feature names, metrics, threshold) saved to model_metadata.pkl."),
        ("Session Model Save", "model_training.py", "Saves to models/sessions/{uuid}/best_model.pkl, scaler.pkl, "
         "model_metadata.pkl. Does NOT overwrite models/base/."),
        ("Inference", "prediction_engine.py", "Same as Predict Only but loads from session model dir, not base dir."),
    ]
    for step, module, desc in steps_retrain:
        story.append(Paragraph(f"<b>{step}</b>  <i>({module})</i>", s["h3"]))
        story.append(Paragraph(desc, s["body"]))
    story.append(PageBreak())

    # ── Section 4: Feature Engineering ──
    story.append(Paragraph("4. Feature Engineering — All Computed Signals", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph("4.1  Engagement Score", s["h2"]))
    story.append(Paragraph(
        "engagement_score = (total_interactions / 15) × 40  +  (avg_satisfaction / 5) × 30  "
        "+  has_autopay × 15  +  paperless_billing × 15", s["code"]))
    story.append(Paragraph(
        "Range: 0–100. Clipped to [0,1] per component before weighting. "
        "A customer with 5 interactions (norm=0.33), satisfaction 2/5 (norm=0.40), "
        "no autopay, no paperless → score = 13.2 + 12.0 + 0 + 0 = 25.2 (low engagement).", s["body"]))

    story.append(Paragraph("4.2  Risk Flags (Binary, 0 or 1)", s["h2"]))
    flags = [
        ["Flag", "Threshold / Logic", "Reasoning"],
        ["complaint_risk_flag", "complaint_count > 3  OR  avg_complaint_severity > 3.5",
         "More than 3 complaints or high severity = persistent dissatisfaction."],
        ["low_satisfaction_flag", "avg_satisfaction_score < 2.5",
         "Below 2.5/5 means more than half interactions rated poorly."],
        ["high_negative_sentiment_flag", "negative_sentiment_ratio > 0.5",
         "Majority of VADER-scored comments are negative (compound < 0)."],
        ["very_negative_sentiment_flag", "avg_sentiment_score < -0.3",
         "Average VADER compound below -0.3 captures 'politely furious' customers."],
        ["sentiment_volatile_flag", "sentiment_std > 0.5",
         "High variance in sentiment = customer is unstable / on the fence."],
        ["new_customer_flag", "account_tenure_months < 12",
         "First year is the danger zone. Churn rate 2-3× higher."],
        ["frequent_caller_flag", "interactions_per_month > 2",
         "Calling more than twice monthly means issues aren't resolving."],
        ["unresolved_issues_flag", "unresolved_complaints > 0  OR  unresolved_count > 1",
         "Open wounds. Every unresolved complaint erodes goodwill."],
    ]
    story.append(info_table(flags, [4.2*cm, 5.5*cm, 6.9*cm]))

    story.append(Paragraph("4.3  Composite Risk Score", s["h2"]))
    story.append(Paragraph(
        "composite_risk_score = sum of all 8 flags above", s["code"]))
    story.append(Paragraph(
        "Range 0–8. A customer scoring 5+ is in serious danger. "
        "This is the single most interpretable feature for retention teams.", s["body"]))
    story.append(PageBreak())

    # ── Section 5: Model ──
    story.append(Paragraph("5. Machine Learning Model — Training & Inference", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph("5.1  Model Ensemble", s["h2"]))
    models_tbl = [
        ["Model", "Key Parameters", "Role in Ensemble"],
        ["Logistic Regression", "max_iter=1000, C=1.0, solver=lbfgs", "Linear baseline, strong on well-separated features"],
        ["Random Forest", "n_estimators=300, max_depth=None", "Handles non-linear patterns, robust to outliers"],
        ["Gradient Boosting", "n_estimators=200, learning_rate=0.1", "Sequential error correction, high accuracy"],
        ["LightGBM", "n_estimators=300, learning_rate=0.05, num_leaves=31", "Fast, memory-efficient, best on tabular data"],
        ["VotingClassifier", "voting='soft', weights=[1,1,1,1]", "Average of all 4 probabilities → final score"],
    ]
    story.append(info_table(models_tbl, [3.5*cm, 6.0*cm, 7.1*cm]))

    story.append(Paragraph("5.2  Base Model Performance (models/base/)", s["h2"]))
    story.append(Paragraph(
        "Training set: 15,000 synthetic customers. Churn rate: 23%. 80/20 train/test split, stratified.", s["body"]))
    perf = [
        ["Metric", "Value", "Notes"],
        ["ROC AUC", "0.828", "Ensemble model on held-out test set (3,000 customers)"],
        ["Accuracy", "80.0%", "At default threshold 0.50"],
        ["Churn Rate (train)", "23%", "Sigmoid threshold 0.45 used during label generation"],
        ["Features used", "~50", "Including all risk flags, engagement score, raw aggregates"],
        ["Training data", "Synthetic", "Generated by data_generator.py — NOT real customer data"],
    ]
    story.append(info_table(perf, [4.0*cm, 3.5*cm, 9.1*cm]))

    story.append(Paragraph("5.3  Inference Path", s["h2"]))
    story.append(Paragraph(
        "1. Load feature_names from model_metadata.pkl\n"
        "2. Align uploaded data columns to feature_names (fill missing with 0)\n"
        "3. scaler.transform(X) — same scaler fitted during training\n"
        "4. model.predict_proba(X)[:, 1] → churn_probability for each customer\n"
        "5. Apply risk tier: High ≥ 0.70, Medium 0.40–0.69, Low < 0.40\n"
        "6. Return sorted DataFrame with probability, tier, top flags", s["code"]))
    story.append(PageBreak())

    # ── Section 6: NuroStudio ──
    story.append(Paragraph("6. NuroStudio AI Assistant — Architecture", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph(
        "NuroStudio is the AI assistant embedded in the platform (AI Assistant tab). It gives "
        "retention teams a conversational interface to interrogate predictions, understand customer "
        "risk, and get retention strategy advice.", s["body"]))
    story.append(Paragraph("6.1  API Fallback Chain", s["h2"]))
    story.append(Paragraph(
        "1. NuroStudio API (primary) — proprietary endpoint, domain-tuned\n"
        "2. Claude API by Anthropic (fallback) — claude-sonnet model\n"
        "3. Rule-based fallback responses — if both APIs unavailable", s["code"]))
    story.append(Paragraph("6.2  Key Parameters", s["h2"]))
    params = [
        ["Parameter", "Value", "Reason"],
        ["MAX_INPUT_CHARS", "5,000", "Context window cost control"],
        ["Message history cap", "50 messages", "Prevents unbounded context growth"],
        ["System prompt", "Domain-specific: utility churn, SAP IS-U context", "Keeps answers relevant"],
        ["Temperature", "Default (API controlled)", "Balanced creativity vs accuracy"],
    ]
    story.append(info_table(params, [4.0*cm, 4.5*cm, 8.1*cm]))
    story.append(Paragraph("6.3  What It Can Answer", s["h2"]))
    for item in [
        "Why is Customer X flagged as High Risk?",
        "What retention script should I use for a customer with unresolved complaints?",
        "What does a composite_risk_score of 6 mean?",
        "Which customers in my upload are most likely to respond to an autopay discount?",
        "Explain the difference between engagement_score and composite_risk_score.",
        "What is the industry standard churn rate for utilities?",
    ]:
        story.append(Paragraph(f"• {item}", s["bullet"]))
    story.append(PageBreak())

    # ── Section 7: Session Isolation ──
    story.append(Paragraph("7. Session Isolation & Multi-User Architecture", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph(
        "Every user (registered or anonymous) gets a UUID-based session_id. This ID keys all "
        "file paths so users never see each other's data.", s["body"]))
    story.append(Paragraph(
        "  Anonymous:   session_id = uuid4() on first load — lost on browser close\n"
        "  Registered:  session_id stored in accounts.json → persists across logins\n"
        "\n"
        "  data/sessions/{id}/        ← uploaded CSVs, merged data, features, history\n"
        "  models/sessions/{id}/      ← custom trained models (Full Analysis)\n"
        "  reports/sessions/{id}/     ← EDA charts", s["code"]))
    story.append(Paragraph(
        "get_session_dirs(session_id) in config.py returns a dict of all 3 paths. "
        "Every pipeline function accepts dirs=None and falls back to global constants when None.", s["body"]))
    story.append(Paragraph("7.1  Session Restore on Login", s["h2"]))
    story.append(Paragraph(
        "restore_session_from_disk() is called at the top of render_upload_tab() on every rerun. "
        "It checks for last_results.csv and pre-generates PDF/Excel bytes, storing everything "
        "in st.session_state so download buttons work immediately without re-running the pipeline.", s["body"]))

    # ── Section 8: Auth ──
    story.append(Paragraph("8. Registration, Auth & Security", s["h1"]))
    section_rule(story, s)
    auth = [
        ["Aspect", "Implementation"],
        ["Password hashing", "hashlib.pbkdf2_hmac('sha256', password, salt, 260000). Salt: os.urandom(32)."],
        ["Timing-safe compare", "hmac.compare_digest(stored_hash, computed_hash) — prevents timing attacks."],
        ["File locking", "fcntl.flock(fd, LOCK_EX) on accounts.json before every read/write cycle."],
        ["Account storage", "storage/accounts.json — gitignored. .gitkeep anchors the directory."],
        ["Lead capture", "storage/leads.json — name, email, company, phone on registration."],
        ["Free tier limit", "FREE_TIER_LIMIT = 5,000 customers per upload. Checked in upload_tab.py."],
        ["Session persistence", "Registered users: permanent session_id in accounts.json. Re-applied on login."],
        ["Password minimum", "8 characters enforced in registration form."],
    ]
    story.append(info_table(auth, [5.0*cm, 11.6*cm]))

    story.append(Paragraph("8.1  GSHEET / EMAIL Webhooks (Not Yet Wired)", s["h2"]))
    story.append(Paragraph(
        "GSHEET_WEBHOOK and EMAIL_WEBHOOK env vars exist in registration.py but are not connected "
        "to live endpoints. Leads currently save only to storage/leads.json. "
        "Priority: wire to real Google Sheet and email provider before client go-live.", s["note"]))
    story.append(PageBreak())

    # ── Section 9: Base Model Training ──
    story.append(Paragraph("9. Base Model — Training Protocol", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph(
        "Run: venv/bin/python scripts/train_base_model.py", s["code"]))
    story.append(Paragraph("What it does:", s["h2"]))
    for item in [
        "Generates 15,000 synthetic customers via data_generator.py (master + complaints + interactions).",
        "Runs full preprocess_pipeline(dirs=base_dirs) — merges and runs VADER on comments.",
        "Runs engineer_features(df, dirs=base_dirs) — computes all 50 features.",
        "Runs training_pipeline(df, dirs=base_dirs) — trains 5 models, picks best by ROC AUC.",
        "Saves best_model.pkl, scaler.pkl, model_metadata.pkl to models/base/.",
        "Prints final metrics: accuracy, ROC AUC, churn rate, feature importances.",
    ]:
        story.append(Paragraph(f"• {item}", s["bullet"]))
    story.append(Paragraph(
        "CRITICAL: models/base/ is committed to git. After retraining, commit the new pkl files. "
        "The auto-restore in _base_model_exists() relies on git restore models/base/ — "
        "this only works if the files are committed.", s["note"]))

    # ── Section 10: Validation ──
    story.append(Paragraph("10. Validation Metrics & Acceptance Criteria", s["h1"]))
    section_rule(story, s)
    val = [
        ["Metric", "Acceptable", "Target", "How to Check"],
        ["ROC AUC", "≥ 0.75", "≥ 0.85", "Logged in model_metadata.pkl after training"],
        ["Accuracy", "≥ 75%", "≥ 82%", "Logged in model_metadata.pkl"],
        ["Churn rate in output", "15–30%", "Match client's known rate", "Count High+Medium risk / total"],
        ["Precision (High Risk)", "≥ 55%", "≥ 70%", "Validate against known outcomes after 90 days"],
        ["Lift (top 20% vs bottom 20%)", "≥ 2×", "≥ 4×", "Compare churn rate in top/bottom quintile"],
        ["Data leakage check", "Comments NOT keyed to churn", "—", "VADER scores should not be 1.0 correlation with labels"],
        ["Churn label sanity", "Both 0 and 1 present in labels", "—", "Check value_counts on churned column"],
    ]
    story.append(info_table(val, [4.2*cm, 2.5*cm, 2.5*cm, 7.4*cm]))

    # ── Section 11: Deployment ──
    story.append(Paragraph("11. Deployment & Infrastructure Notes", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph("Current state: local Streamlit server. Production options:", s["body"]))
    deploy = [
        ["Platform", "Pros", "Cons", "Estimated Cost"],
        ["Hugging Face Spaces", "Free tier, easy deploy, Dockerfile support", "Cold starts, limited CPU", "$0–$50/mo"],
        ["Railway", "One-click deploy, persistent volumes, custom domain", "Limited free tier", "$20–$100/mo"],
        ["Render", "Auto-deploy from git, SSL included", "Spin-down on free tier", "$7–$50/mo"],
        ["AWS EC2 / GCP VM", "Full control, scalable", "Requires DevOps knowledge", "$30–$200/mo"],
    ]
    story.append(info_table(deploy, [3.5*cm, 5.0*cm, 4.5*cm, 3.6*cm]))
    story.append(Paragraph(
        "Priority before production: wire GSHEET_WEBHOOK, EMAIL_WEBHOOK, add HTTPS, "
        "add pricing tier enforcement beyond the 5,000 customer check.", s["note"]))

    # ── Section 12: Roadmap ──
    story.append(Paragraph("12. Known Limitations & Roadmap", s["h1"]))
    section_rule(story, s)
    lims = [
        ["Item", "Current State", "Fix Required"],
        ["Base model data", "Synthetic 15k customers", "Retrain on real client data after first deployment"],
        ["Dashboard data", "Always shows demo 5k synthetic", "Wire uploaded data results to Dashboard tab"],
        ["Customer Lookup", "Only works after Run Demo", "Load from session data after upload"],
        ["Google Sheets", "Not wired", "Set GSHEET_WEBHOOK env var to real webhook URL"],
        ["Email on signup", "Not wired", "Set EMAIL_WEBHOOK env var"],
        ["Pricing page", "No upgrade path UI", "Build upgrade flow beyond FREE_TIER_LIMIT"],
        ["Scheduled runs", "Not implemented", "Cron job or Streamlit scheduler"],
        ["Audit log", "Not implemented", "Log all uploads + predictions per user for compliance"],
    ]
    story.append(info_table(lims, [3.8*cm, 5.0*cm, 7.8*cm]))

    story.append(Spacer(1,1.0*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=CYAN, spaceAfter=8))
    story.append(Paragraph(
        "INTERNAL DOCUMENT — CONFIDENTIAL · Vantive Inc. · raj.konka@vantiveinc.com · © 2026",
        s["footer"]))

    doc.build(story)
    print(f"[1/4] Internal PDF: {path}")


# ═══════════════════════════════════════════════════════════════
#  PDF 2 — CLIENT SALES BRIEF
# ═══════════════════════════════════════════════════════════════

def build_client_pdf():
    path = os.path.join(OUT, "Vantive_Client_Brief.pdf")
    doc  = SimpleDocTemplate(path, pagesize=A4,
           leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.2*cm, bottomMargin=2.2*cm)
    s    = base_styles()
    story= []

    # Cover
    title_tbl = Table([[Paragraph(
        "Customer Retention<br/>Intelligence Platform",
        ParagraphStyle("ct",fontSize=26,textColor=WHITE,leading=34,
                       fontName="Helvetica-Bold",alignment=TA_CENTER)
    )]], colWidths=[16.6*cm])
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY),
        ("TOPPADDING",(0,0),(-1,-1),40),("BOTTOMPADDING",(0,0),(-1,-1),40),
    ]))
    story.append(title_tbl); story.append(Spacer(1,0.3*cm))
    story.append(cover_band("AI-Powered Churn Prevention for Utility Companies", BLUE, WHITE))
    story.append(Spacer(1,0.3*cm))
    story.append(cover_band("Vantive Inc.  ·  raj.konka@vantiveinc.com  ·  2026", NAVY, CYAN))
    story.append(Spacer(1,1.2*cm))

    # Executive Summary
    story.append(Paragraph("Executive Summary", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph(
        "Utility companies lose an average of <b>15–25% of customers every year</b>. Most of that "
        "churn is preventable — customers signal their intention to leave weeks or months before "
        "they actually cancel. The problem is that no one is reading those signals in time.", s["body"]))
    story.append(Paragraph(
        "The Vantive Customer Retention Intelligence Platform changes that. It reads your existing "
        "customer data — complaints, interactions, billing behaviour, satisfaction scores — and tells "
        "you <b>exactly which customers are about to leave and why</b>, giving your retention team "
        "time to act before it's too late.", s["body"]))
    story.append(Spacer(1,0.4*cm))

    # KPI row
    kpi_data = [[
        Paragraph("15–25%", s["kpi_num"]),
        Paragraph("$300+", s["kpi_num"]),
        Paragraph("10×", s["kpi_num"]),
        Paragraph("< 2 min", s["kpi_num"]),
    ],[
        Paragraph("annual churn rate\naverage utility", s["kpi_lbl"]),
        Paragraph("cost to acquire\none new customer", s["kpi_lbl"]),
        Paragraph("cheaper to retain\nthan acquire", s["kpi_lbl"]),
        Paragraph("time to results\nafter upload", s["kpi_lbl"]),
    ]]
    kpi_tbl = Table(kpi_data, colWidths=[4.15*cm]*4)
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),LIGHT),
        ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#CFD8DC")),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    story.append(kpi_tbl); story.append(Spacer(1,0.8*cm))

    # What You Get
    story.append(Paragraph("What You Get", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph(
        "Upload your customer data. Within two minutes you receive:", s["body"]))
    deliverables = [
        ("A ranked risk list of every customer",
         "Sorted from highest to lowest churn risk. Every customer gets a risk score from 0–100%."),
        ("High / Medium / Low risk tiers",
         "Your retention team knows who to call today (High Risk), who to monitor (Medium), "
         "and who is healthy (Low). No guesswork."),
        ("Plain-language reasons for each customer",
         "Not just a number — the platform tells you WHY each customer is at risk. "
         "'Unresolved complaint + called 4× this month + satisfaction score 1.8/5' is actionable. A number is not."),
        ("Specific retention recommendations",
         "Based on the risk profile, the platform recommends a tailored action: proactive outreach call, "
         "billing dispute resolution, loyalty discount, or escalation to account manager."),
        ("NuroStudio AI Assistant",
         "An embedded AI assistant your team can ask questions in plain English: "
         "'What should I say to a customer with 6 unresolved complaints?' "
         "'Which customers are most likely to respond to an autopay incentive?'"),
        ("PDF and Excel reports",
         "Download a formatted PDF summary or a 4-sheet Excel workbook instantly — "
         "ready to share with your leadership team or retention agents."),
        ("Run history",
         "Every upload is saved. Log in next week, next month — your previous results and "
         "downloads are waiting for you."),
    ]
    for title, desc in deliverables:
        story.append(Paragraph(f"<b>{title}</b>", s["h3"]))
        story.append(Paragraph(desc, s["body"]))
    story.append(PageBreak())

    # How It Works (client-friendly, no logic)
    story.append(Paragraph("How It Works", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph(
        "The platform is designed to require zero technical knowledge. Here is what happens "
        "when you upload your data:", s["body"]))
    how_data = [
        ["Step", "What You Do", "What the Platform Does"],
        ["1", "Upload your files (CSV or Excel)", "Automatically maps your columns to the right fields — even if your column names are different from ours."],
        ["2", "Click 'Score My Customers'", "Reads your complaint records, satisfaction scores, interaction history, and billing data. Runs NLP analysis on complaint text."],
        ["3", "Wait ~90 seconds", "Scores every customer. Assigns risk tier. Identifies the top reasons each customer is at risk."],
        ["4", "Review your results", "Sorted risk list appears. Filter by High / Medium / Low. See reasons and recommendations per customer."],
        ["5", "Download your reports", "PDF summary and Excel workbook ready instantly. One click each."],
        ["6", "Take action", "Give High Risk list to your retention team. Act before customers cancel."],
    ]
    story.append(info_table(how_data, [1.5*cm, 4.5*cm, 10.6*cm]))
    story.append(Spacer(1,0.8*cm))

    # NuroStudio
    story.append(Paragraph("NuroStudio — Your AI Retention Advisor", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph(
        "Built into the platform is NuroStudio — an AI assistant trained to help your team "
        "understand customer risk and take the right action. It understands the context of your "
        "utility business and speaks your language.", s["body"]))
    story.append(Paragraph("What your team can ask NuroStudio:", s["h2"]))
    questions = [
        "\"This customer has a risk score of 87% — what should I say when I call them?\"",
        "\"We have 200 high-risk customers. Which segment should we prioritise first?\"",
        "\"What is the most effective retention offer for customers who are disputing a bill?\"",
        "\"Explain to me in simple terms why this customer is flagged as high risk.\"",
        "\"What are the early warning signs of churn we should watch for this quarter?\"",
    ]
    for q in questions:
        story.append(Paragraph(f"• {q}", s["bullet"]))
    story.append(Paragraph(
        "NuroStudio is always available in the AI Assistant tab. No training required — "
        "just ask your question in plain English.", s["body"]))
    story.append(Spacer(1,0.5*cm))

    # Getting More Accurate Over Time
    story.append(Paragraph("Getting More Accurate Over Time", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph(
        "The platform is ready to use on day one. As your team uploads more data over time — "
        "especially historical data that includes which customers actually churned — the platform "
        "learns your specific customer base and becomes more accurate for your market.", s["body"]))
    story.append(Paragraph(
        "This is exactly how the world's largest telecoms and utility companies operate their "
        "AI retention programmes. The difference is that those systems cost millions to build. "
        "This one is ready to deploy today.", s["body"]))
    story.append(Spacer(1,0.5*cm))

    # Business Case
    story.append(Paragraph("The Business Case", s["h1"]))
    section_rule(story, s)
    roi_data = [
        ["Scenario", "Number"],
        ["Your customer base", "50,000 customers"],
        ["Current annual churn rate", "20% = 10,000 customers lost per year"],
        ["Average annual revenue per customer", "$1,200"],
        ["Revenue lost to churn each year", "$12,000,000"],
        ["Cost of a proactive retention call or offer", "$20–$50 per customer"],
        ["If you prevent just 10% of churn (1,000 customers)", "$1,200,000 revenue retained"],
        ["Cost to prevent it (1,000 × $50)", "$50,000"],
        ["Net return on investment", "$1,150,000  ·  2,300% ROI"],
    ]
    roi_tbl = Table(roi_data, colWidths=[10.0*cm, 6.6*cm])
    roi_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),
        ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),10),
        ("ROWBACKGROUNDS",(0,1),(-1,-2),[LIGHT,WHITE]),
        ("BACKGROUND",(0,-1),(-1,-1),ORANGE),
        ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
        ("TEXTCOLOR",(0,-1),(-1,-1),NAVY),
        ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#CFD8DC")),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
    ]))
    story.append(roi_tbl); story.append(Spacer(1,0.8*cm))

    # Security
    story.append(Paragraph("Security & Data Privacy", s["h1"]))
    section_rule(story, s)
    for item in [
        "Your data is <b>never shared</b> with other organisations. Every user's data is isolated in their own private workspace.",
        "All passwords are encrypted using <b>industry-standard hashing</b> (the same standard used by banks and government systems).",
        "You can <b>download and delete your data</b> at any time.",
        "The platform can be deployed on <b>your own infrastructure</b> for maximum data sovereignty — available on request.",
    ]:
        story.append(Paragraph(f"• {item}", s["bullet"]))
    story.append(Spacer(1,0.8*cm))

    # Next Steps
    story.append(Paragraph("Next Steps", s["h1"]))
    section_rule(story, s)
    story.append(Paragraph(
        "We offer a <b>free trial</b> — upload up to 5,000 of your customer records and see "
        "your first risk report at no cost, with no commitment.", s["body"]))
    story.append(Paragraph(
        "To get started or to schedule a live demonstration with your team:", s["body"]))
    story.append(Spacer(1,0.3*cm))

    contact_data = [[
        Paragraph("Raj Konka\nVantive Inc.", ParagraphStyle("c1",fontSize=11,textColor=NAVY,
                   fontName="Helvetica-Bold",leading=16)),
        Paragraph("raj.konka@vantiveinc.com\nkonkarajkumar12@gmail.com",
                  ParagraphStyle("c2",fontSize=10,textColor=BLUE,fontName="Helvetica",leading=16)),
    ]]
    ct = Table(contact_data, colWidths=[8.0*cm, 8.6*cm])
    ct.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),LIGHT),
        ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#CFD8DC")),
        ("TOPPADDING",(0,0),(-1,-1),14),("BOTTOMPADDING",(0,0),(-1,-1),14),
        ("LEFTPADDING",(0,0),(-1,-1),14),
    ]))
    story.append(ct)
    story.append(Spacer(1,1.0*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=CYAN, spaceAfter=8))
    story.append(Paragraph(
        "© 2026 Vantive Inc. All rights reserved. This document is confidential and intended "
        "solely for the recipient named above.", s["footer"]))

    doc.build(story)
    print(f"[2/4] Client PDF: {path}")


# ═══════════════════════════════════════════════════════════════
#  SHARED PPT HELPERS
# ═══════════════════════════════════════════════════════════════

def new_prs():
    prs = Presentation()
    prs.slide_width  = Inches(W)
    prs.slide_height = Inches(H)
    return prs

def blank(prs): return prs.slides.add_slide(prs.slide_layouts[6])

def bg(slide, c): slide.background.fill.solid(); slide.background.fill.fore_color.rgb = c

def rect(slide, l, t, w, h, fill, line=None, line_w=Pt(1)):
    sh = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line: sh.line.color.rgb = line; sh.line.width = line_w
    else:     sh.line.fill.background()
    return sh

def txt(slide, text, l, t, w, h, size=16, bold=False, color=WHITE_R,
        align=PP_ALIGN.LEFT, italic=False, wrap=True, line_spacing=None):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = wrap
    if line_spacing: tf.paragraphs[0].line_spacing = line_spacing
    p = tf.paragraphs[0]; p.alignment = align
    r = p.add_run(); r.text = text
    r.font.size = Pt(size); r.font.bold = bold
    r.font.italic = italic; r.font.color.rgb = color
    return tb

def slide_header(slide, title, subtitle=None):
    rect(slide, 0, 0, W, 1.15, BLUE_R)
    rect(slide, 0, 0, 0.08, 1.15, CYAN_R)
    txt(slide, title, 0.25, 0.1, W-0.5, 0.65, size=30, bold=True, color=WHITE_R)
    if subtitle:
        txt(slide, subtitle, 0.25, 0.72, W-0.5, 0.38, size=13, color=LIGHT_R)

def slide_footer(slide, text="Vantive Inc.  ·  raj.konka@vantiveinc.com  ·  Confidential"):
    rect(slide, 0, H-0.28, W, 0.28, NAVY_R)
    txt(slide, text, 0.3, H-0.26, W-0.6, 0.24, size=9, color=GREY_R, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════
#  PPT 1 — INTERNAL TECHNICAL DECK
# ═══════════════════════════════════════════════════════════════

def build_internal_pptx():
    prs = new_prs()
    path = os.path.join(OUT, "Vantive_Internal_Technical_Deck.pptx")

    # ── Slide 1: Cover ──
    sl = blank(prs); bg(sl, DARK_R)
    rect(sl, 0, 0, W, 0.12, CYAN_R); rect(sl, 0, H-0.12, W, 0.12, CYAN_R)
    rect(sl, 0, 0.12, 0.12, H-0.24, NAVY_R)
    txt(sl, "SAP IS-U CUSTOMER RETENTION SYSTEM", 0.5, 1.4, W-1.0, 0.9,
        size=34, bold=True, color=WHITE_R, align=PP_ALIGN.CENTER)
    txt(sl, "INTERNAL TECHNICAL REFERENCE DECK", 0.5, 2.35, W-1.0, 0.55,
        size=18, bold=True, color=CYAN_R, align=PP_ALIGN.CENTER)
    rect(sl, 3.5, 3.1, 6.33, 0.06, ORANGE_R)
    txt(sl, "Version 3.0  ·  Vantive Inc.  ·  2026  ·  CONFIDENTIAL",
        0.5, 3.3, W-1.0, 0.45, size=13, color=GREY_R, align=PP_ALIGN.CENTER)
    txt(sl, "raj.konka@vantiveinc.com  ·  konkarajkumar12@gmail.com",
        0.5, 3.85, W-1.0, 0.4, size=13, color=LIGHT_R, align=PP_ALIGN.CENTER)

    # ── Slide 2: Architecture Overview ──
    sl = blank(prs); bg(sl, NAVY_R)
    slide_header(sl, "System Architecture", "Full technical stack and data flow")
    slide_footer(sl)
    layers = [
        ("FRONTEND", "Streamlit ≥1.30", "5 tabs, session state, CSS theming, sidebar"),
        ("ML CORE",  "scikit-learn + LightGBM", "LR, RF, GBM, LGBM, Ensemble — joblib serialisation"),
        ("NLP",      "VADER (NLTK)", "Complaint text → compound score -1.0 to +1.0"),
        ("DATA I/O", "pandas, openpyxl, PyMuPDF", "CSV/Excel/PDF/Word/JSON ingestion + fuzzy mapping"),
        ("REPORTS",  "matplotlib PdfPages + openpyxl", "Multi-page PDF + 4-sheet XLSX export"),
        ("AI ASSIST","NuroStudio → Claude API", "Conversational AI with domain context + fallback chain"),
        ("AUTH",     "PBKDF2-SHA256, 260k iter", "Timing-safe compare_digest, fcntl file locking"),
        ("STORAGE",  "Local filesystem (UUID-keyed)", "data/sessions/, models/sessions/, storage/"),
    ]
    for i, (layer, tech, detail) in enumerate(layers):
        col = i % 2; row = i // 2
        x = 0.3 + col * 6.55; y = 1.35 + row * 1.46
        rect(sl, x, y, 6.2, 1.3, BLUE_R)
        rect(sl, x, y, 1.8, 1.3, CYAN_R)
        txt(sl, layer, x+0.05, y+0.3, 1.7, 0.6, size=11, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
        txt(sl, tech,  x+1.9, y+0.05, 4.2, 0.45, size=13, bold=True, color=ORANGE_R)
        txt(sl, detail,x+1.9, y+0.52, 4.2, 0.65, size=10, color=WHITE_R)

    # ── Slide 3: File Structure ──
    sl = blank(prs); bg(sl, NAVY_R)
    slide_header(sl, "File Structure & Module Map", "What each file owns")
    slide_footer(sl)
    files_left = [
        ("app.py", "Entry point. 5 tabs. Session dirs. CSS."),
        ("config.py", "Constants, get_session_dirs(id)"),
        ("src/registration.py", "Auth. PBKDF2. fcntl. storage/"),
        ("src/upload_tab.py", "Upload UI. Auto detect. _predict_only, _retrain."),
        ("src/data_upload.py", "File read. Fuzzy map ≥0.75. Table detect."),
        ("src/data_preprocessing.py", "Merge 3 tables. VADER NLP."),
    ]
    files_right = [
        ("src/feature_engineering.py", "50 features. 8 flags. engagement_score."),
        ("src/model_training.py", "Train 5 models. Best by ROC AUC."),
        ("src/prediction_engine.py", "ChurnPredictor. predict_proba. Risk tiers."),
        ("src/chatbot.py", "NuroStudio → Claude → fallback."),
        ("src/report_generator.py", "PDF (PdfPages) + Excel (openpyxl)."),
        ("scripts/train_base_model.py", "Train base model → models/base/."),
    ]
    for i, (f, d) in enumerate(files_left):
        y = 1.35 + i * 0.98
        rect(sl, 0.3, y, 6.2, 0.85, BLUE_R)
        txt(sl, f, 0.45, y+0.05, 6.0, 0.38, size=11, bold=True, color=CYAN_R)
        txt(sl, d, 0.45, y+0.44, 6.0, 0.38, size=10, color=WHITE_R)
    for i, (f, d) in enumerate(files_right):
        y = 1.35 + i * 0.98
        rect(sl, 6.83, y, 6.2, 0.85, BLUE_R)
        txt(sl, f, 6.98, y+0.05, 6.0, 0.38, size=11, bold=True, color=CYAN_R)
        txt(sl, d, 6.98, y+0.44, 6.0, 0.38, size=10, color=WHITE_R)

    # ── Slide 4: Pipeline — Predict Only ──
    sl = blank(prs); bg(sl, NAVY_R)
    slide_header(sl, "Pipeline: Predict Only Mode", "No churned column in uploaded data → uses models/base/")
    slide_footer(sl)
    steps = [
        ("Upload +\nMap", "data_upload.py\nFuzzy match ≥0.75"),
        ("Infer\nLabels", "infer_churn_labels()\nSigmoid threshold 0.45"),
        ("Preprocess\n+ Merge", "preprocess_pipeline()\n3 tables → 1 record"),
        ("VADER\nNLP", "SentimentIntensity\nAnalyzer on comments"),
        ("Feature\nEngineering", "engineer_features()\n50 signals"),
        ("Base Model\nLoad", "_base_model_exists()\ngit restore fallback"),
        ("Scale +\nInfer", "scaler.transform(X)\npredict_proba[:,1]"),
        ("Risk Tier\n+ Render", "≥0.70 High\n0.40–0.69 Med"),
    ]
    for i, (title, detail) in enumerate(steps):
        x = 0.2 + i * 1.62
        rect(sl, x, 1.35, 1.5, 2.5, BLUE_R)
        rect(sl, x, 1.35, 1.5, 0.5, CYAN_R)
        txt(sl, str(i+1), x, 1.35, 1.5, 0.5, size=20, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
        txt(sl, title, x+0.05, 1.88, 1.4, 0.75, size=11, bold=True, color=ORANGE_R, align=PP_ALIGN.CENTER)
        txt(sl, detail, x+0.05, 2.7, 1.4, 1.0, size=9, color=WHITE_R, align=PP_ALIGN.CENTER)
        if i < 7:
            txt(sl, "→", x+1.42, 1.9, 0.3, 0.5, size=18, bold=True, color=CYAN_R)
    txt(sl, "Session state stores results + PDF bytes + XLSX bytes on every rerun → download buttons work without re-running pipeline.",
        0.3, 4.1, W-0.6, 0.5, size=11, color=LIGHT_R)
    txt(sl, "History: _save_run_to_history() → run_history.json + last_results.csv → restore_session_from_disk() on next login.",
        0.3, 4.65, W-0.6, 0.5, size=11, color=LIGHT_R)

    # ── Slide 5: Feature Engineering ──
    sl = blank(prs); bg(sl, NAVY_R)
    slide_header(sl, "Feature Engineering — All 50 Signals", "What we compute per customer before the model sees the data")
    slide_footer(sl)
    txt(sl, "Engagement Score  =  (interactions/15)×40  +  (satisfaction/5)×30  +  autopay×15  +  paperless×15   →  range 0–100",
        0.3, 1.25, W-0.6, 0.5, size=12, bold=True, color=ORANGE_R)
    flags = [
        ("complaint_risk_flag",          "complaint_count > 3  OR  avg_severity > 3.5"),
        ("low_satisfaction_flag",        "avg_satisfaction_score < 2.5"),
        ("high_negative_sentiment_flag", "negative_sentiment_ratio > 0.5"),
        ("very_negative_sentiment_flag", "avg_sentiment_score < -0.3"),
        ("sentiment_volatile_flag",      "sentiment_std > 0.5"),
        ("new_customer_flag",            "account_tenure_months < 12"),
        ("frequent_caller_flag",         "interactions_per_month > 2"),
        ("unresolved_issues_flag",       "unresolved_complaints > 0  OR  unresolved_count > 1"),
    ]
    for i, (flag, threshold) in enumerate(flags):
        col = i % 2; row = i // 2
        x = 0.3 + col * 6.55; y = 1.85 + row * 1.18
        rect(sl, x, y, 6.2, 1.05, BLUE_R)
        txt(sl, flag, x+0.15, y+0.07, 6.0, 0.42, size=12, bold=True, color=CYAN_R)
        txt(sl, threshold, x+0.15, y+0.55, 6.0, 0.42, size=11, color=WHITE_R)
    txt(sl, "composite_risk_score  =  sum of all 8 flags  →  range 0–8   (5+ = serious danger zone)",
        0.3, 6.6, W-0.6, 0.45, size=12, bold=True, color=ORANGE_R)

    # ── Slide 6: Model Architecture ──
    sl = blank(prs); bg(sl, NAVY_R)
    slide_header(sl, "ML Model — Ensemble Architecture", "5 models trained, best selected by ROC AUC on held-out test set")
    slide_footer(sl)
    models = [
        ("Logistic Regression", "max_iter=1000\nC=1.0, lbfgs", "Linear baseline"),
        ("Random Forest",       "n_estimators=300\nmax_depth=None", "Non-linear, outlier robust"),
        ("Gradient Boosting",   "n_estimators=200\nlr=0.1", "Sequential error correction"),
        ("LightGBM",            "n_estimators=300\nlr=0.05, leaves=31", "Fast, memory-efficient"),
    ]
    for i, (name, params, role) in enumerate(models):
        x = 0.3 + i * 3.2; y = 1.35
        rect(sl, x, y, 3.0, 2.8, BLUE_R)
        rect(sl, x, y, 3.0, 0.5, CYAN_R)
        txt(sl, str(i+1), x, y+0.03, 3.0, 0.45, size=18, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
        txt(sl, name, x+0.1, y+0.58, 2.8, 0.6, size=13, bold=True, color=ORANGE_R, align=PP_ALIGN.CENTER)
        txt(sl, params, x+0.1, y+1.25, 2.8, 0.8, size=10, color=WHITE_R, align=PP_ALIGN.CENTER)
        txt(sl, role, x+0.1, y+2.1, 2.8, 0.55, size=10, color=LIGHT_R, align=PP_ALIGN.CENTER)
    txt(sl, "↓   ↓   ↓   ↓", 0.3, 4.25, W-0.6, 0.5, size=20, bold=True, color=CYAN_R, align=PP_ALIGN.CENTER)
    rect(sl, 2.5, 4.8, 8.33, 1.3, ORANGE_R)
    txt(sl, "VotingClassifier (soft, equal weights) → average of all 4 probabilities → final churn_probability",
        2.6, 4.85, 8.1, 1.1, size=14, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
    txt(sl, "Base Model Performance:  ROC AUC 0.828  ·  Accuracy 80%  ·  Trained on 15,000 synthetic customers  ·  23% churn rate",
        0.3, 6.28, W-0.6, 0.4, size=11, color=GREY_R, align=PP_ALIGN.CENTER)

    # ── Slide 7: NuroStudio Architecture ──
    sl = blank(prs); bg(sl, NAVY_R)
    slide_header(sl, "NuroStudio AI Assistant — Architecture", "Conversational AI layer embedded in the platform")
    slide_footer(sl)
    rect(sl, 0.3, 1.35, 4.0, 5.7, BLUE_R)
    txt(sl, "FALLBACK CHAIN", 0.3, 1.35, 4.0, 0.5, size=14, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
    rect(sl, 0.3, 1.35, 4.0, 0.5, CYAN_R)
    chain = [
        ("1", "NuroStudio API", "Primary endpoint\nDomain-tuned model"),
        ("2", "Claude API (Anthropic)", "Fallback — claude-sonnet\nFull reasoning capability"),
        ("3", "Rule-based responses", "Last resort — no API\nPredefined answer set"),
    ]
    for i, (num, name, detail) in enumerate(chain):
        y = 2.0 + i * 1.6
        rect(sl, 0.5, y, 3.6, 1.4, NAVY_R)
        txt(sl, num, 0.5, y+0.3, 0.7, 0.7, size=22, bold=True, color=ORANGE_R, align=PP_ALIGN.CENTER)
        txt(sl, name, 1.25, y+0.08, 2.8, 0.5, size=12, bold=True, color=CYAN_R)
        txt(sl, detail, 1.25, y+0.6, 2.8, 0.7, size=10, color=WHITE_R)
        if i < 2:
            txt(sl, "↓ if unavailable", 0.5, y+1.45, 3.6, 0.3, size=9, color=GREY_R, align=PP_ALIGN.CENTER)

    rect(sl, 4.6, 1.35, 8.4, 5.7, BLUE_R)
    txt(sl, "PARAMETERS & CONSTRAINTS", 4.6, 1.35, 8.4, 0.5, size=14, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
    rect(sl, 4.6, 1.35, 8.4, 0.5, CYAN_R)
    params = [
        ("MAX_INPUT_CHARS", "5,000", "Context cost control"),
        ("Message history cap", "50 messages", "Prevents unbounded growth"),
        ("System prompt", "Domain-specific", "Utility churn + SAP IS-U context"),
        ("Model (fallback)", "claude-sonnet-4-6", "Latest Anthropic model"),
    ]
    for i, (k, v, reason) in enumerate(params):
        y = 2.05 + i * 1.18
        rect(sl, 4.8, y, 8.0, 1.0, NAVY_R)
        txt(sl, k, 4.95, y+0.05, 4.0, 0.4, size=12, bold=True, color=CYAN_R)
        txt(sl, v, 4.95, y+0.52, 2.5, 0.4, size=14, bold=True, color=ORANGE_R)
        txt(sl, reason, 7.5, y+0.52, 5.0, 0.4, size=10, color=WHITE_R)

    # ── Slide 8: Session Isolation & Auth ──
    sl = blank(prs); bg(sl, NAVY_R)
    slide_header(sl, "Session Isolation, Auth & Security", "Multi-user architecture and security implementation")
    slide_footer(sl)
    rect(sl, 0.3, 1.35, 6.0, 5.7, BLUE_R)
    txt(sl, "SESSION ISOLATION", 0.3, 1.35, 6.0, 0.5, size=14, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
    rect(sl, 0.3, 1.35, 6.0, 0.5, CYAN_R)
    iso_lines = [
        "Every user → UUID session_id",
        "Anonymous: new UUID each session",
        "Registered: permanent ID in accounts.json",
        "",
        "data/sessions/{id}/",
        "  ↳ uploaded CSVs, merged data, features",
        "  ↳ run_history.json, last_results.csv",
        "",
        "models/sessions/{id}/",
        "  ↳ Full Analysis custom model",
        "",
        "reports/sessions/{id}/",
        "  ↳ EDA charts",
        "",
        "get_session_dirs(id) in config.py",
        "All pipeline funcs: dirs=None fallback",
        "",
        "restore_session_from_disk() on login",
        "  ↳ reloads last results + PDF/XLSX bytes",
    ]
    for i, line in enumerate(iso_lines):
        color = ORANGE_R if line.startswith("data/") or line.startswith("models/") or line.startswith("reports/") else WHITE_R
        bold = line.startswith("data/") or line.startswith("models/") or line.startswith("reports/")
        txt(sl, line, 0.5, 1.98 + i*0.21, 5.7, 0.22, size=10, bold=bold, color=color)

    rect(sl, 6.6, 1.35, 6.4, 5.7, BLUE_R)
    txt(sl, "SECURITY", 6.6, 1.35, 6.4, 0.5, size=14, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
    rect(sl, 6.6, 1.35, 6.4, 0.5, CYAN_R)
    sec = [
        ("Hashing", "PBKDF2-SHA256\n260,000 iterations + os.urandom(32) salt"),
        ("Compare", "hmac.compare_digest\n— timing-safe, prevents brute-force timing attack"),
        ("File lock", "fcntl.flock(LOCK_EX)\n— concurrent-safe JSON writes"),
        ("Accounts", "storage/accounts.json\n— gitignored, .gitkeep anchors dir"),
        ("Free tier", "FREE_TIER_LIMIT = 5,000\n— enforced in upload_tab.py"),
        ("Webhooks", "GSHEET_WEBHOOK + EMAIL_WEBHOOK\n— env vars exist, NOT yet wired"),
    ]
    for i, (k, v) in enumerate(sec):
        y = 2.0 + i * 0.87
        rect(sl, 6.8, y, 6.0, 0.78, NAVY_R)
        txt(sl, k, 6.95, y+0.04, 2.0, 0.33, size=11, bold=True, color=CYAN_R)
        txt(sl, v, 6.95, y+0.38, 6.0, 0.38, size=9, color=WHITE_R)

    # ── Slide 9: Validation & Roadmap ──
    sl = blank(prs); bg(sl, NAVY_R)
    slide_header(sl, "Validation Criteria & Known Gaps", "Acceptance thresholds and outstanding work")
    slide_footer(sl)
    rect(sl, 0.3, 1.35, 6.0, 5.7, BLUE_R)
    txt(sl, "VALIDATION METRICS", 0.3, 1.35, 6.0, 0.5, size=14, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
    rect(sl, 0.3, 1.35, 6.0, 0.5, CYAN_R)
    metrics = [
        ("ROC AUC", "≥ 0.75 acceptable · ≥ 0.85 target"),
        ("Accuracy", "≥ 75% acceptable · ≥ 82% target"),
        ("Churn rate", "15–30% predicted · match client known rate"),
        ("Precision (High Risk)", "≥ 55% acceptable · ≥ 70% target"),
        ("Lift", "Top 20% churn ≥ 2× bottom 20%"),
        ("Leakage check", "VADER scores not 1.0 correlated with labels"),
    ]
    for i, (k, v) in enumerate(metrics):
        y = 1.98 + i * 0.8
        rect(sl, 0.5, y, 5.6, 0.72, NAVY_R)
        txt(sl, k, 0.65, y+0.04, 5.3, 0.33, size=12, bold=True, color=ORANGE_R)
        txt(sl, v, 0.65, y+0.38, 5.3, 0.3, size=10, color=WHITE_R)

    rect(sl, 6.6, 1.35, 6.4, 5.7, BLUE_R)
    txt(sl, "OUTSTANDING GAPS", 6.6, 1.35, 6.4, 0.5, size=14, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
    rect(sl, 6.6, 1.35, 6.4, 0.5, CYAN_R)
    gaps = [
        ("Dashboard", "Still shows demo data — not uploaded real data"),
        ("Customer Lookup", "Only works after Run Demo"),
        ("Google Sheets", "GSHEET_WEBHOOK not wired to live sheet"),
        ("Email signup", "EMAIL_WEBHOOK not configured"),
        ("Pricing page", "No upgrade path UI beyond 5k limit"),
        ("Hosting", "Railway/Render/HuggingFace — deferred"),
        ("Audit log", "No per-user action log for compliance"),
    ]
    for i, (k, v) in enumerate(gaps):
        y = 1.98 + i * 0.73
        rect(sl, 6.8, y, 6.0, 0.65, NAVY_R)
        txt(sl, k, 6.95, y+0.04, 5.7, 0.3, size=11, bold=True, color=RED_R)
        txt(sl, v, 6.95, y+0.33, 5.7, 0.3, size=10, color=WHITE_R)

    prs.save(path)
    print(f"[3/4] Internal PPTX: {path}")


# ═══════════════════════════════════════════════════════════════
#  PPT 2 — CLIENT PRESENTATION (STAR METHOD)
# ═══════════════════════════════════════════════════════════════

def build_client_pptx():
    prs  = new_prs()
    path = os.path.join(OUT, "Vantive_Client_Presentation.pptx")

    # ── Slide 1: Cover ──
    sl = blank(prs); bg(sl, DARK_R)
    rect(sl, 0, 0, W, 0.12, CYAN_R); rect(sl, 0, H-0.12, W, 0.12, CYAN_R)
    rect(sl, 0, 0.12, W, 2.2, NAVY_R)
    txt(sl, "CUSTOMER RETENTION", 0.6, 0.35, W-1.2, 0.85, size=44, bold=True, color=WHITE_R, align=PP_ALIGN.CENTER)
    txt(sl, "INTELLIGENCE PLATFORM", 0.6, 1.2, W-1.2, 0.85, size=44, bold=True, color=CYAN_R, align=PP_ALIGN.CENTER)
    rect(sl, 2.0, 2.45, 9.33, 0.07, ORANGE_R)
    txt(sl, "AI-Powered Churn Prevention for Utility Companies",
        0.6, 2.65, W-1.2, 0.55, size=20, color=LIGHT_R, align=PP_ALIGN.CENTER)
    txt(sl, "Vantive Inc.  ·  raj.konka@vantiveinc.com  ·  2026",
        0.6, 6.55, W-1.2, 0.45, size=13, color=GREY_R, align=PP_ALIGN.CENTER)

    # ── Slide 2: STAR — S — Situation ──
    sl = blank(prs); bg(sl, NAVY_R)
    rect(sl, 0, 0, W, 1.2, DARK_R)
    rect(sl, 0, 0, 0.1, 1.2, ORANGE_R)
    txt(sl, "S", 0.2, 0.1, 0.8, 0.9, size=52, bold=True, color=ORANGE_R, align=PP_ALIGN.CENTER)
    txt(sl, "SITUATION", 1.1, 0.1, 4.0, 0.55, size=30, bold=True, color=WHITE_R)
    txt(sl, "The crisis hiding in your customer data", 1.1, 0.65, 9.0, 0.45, size=16, color=CYAN_R)
    slide_footer(sl)

    stats = [
        ("15–25%", "of your customers\nleave every year"),
        ("$300–$500", "cost to acquire\none replacement"),
        ("Weeks", "customers signal intent\nbefore they cancel"),
        ("0", "early warnings seen\nby most utilities"),
    ]
    for i, (num, label) in enumerate(stats):
        x = 0.3 + i * 3.25; y = 1.4
        rect(sl, x, y, 3.0, 2.8, BLUE_R)
        txt(sl, num, x+0.1, y+0.25, 2.8, 1.0, size=38, bold=True, color=ORANGE_R, align=PP_ALIGN.CENTER)
        txt(sl, label, x+0.1, y+1.4, 2.8, 1.0, size=14, color=WHITE_R, align=PP_ALIGN.CENTER)

    rect(sl, 0.3, 4.45, W-0.6, 1.15, BLUE_R)
    rect(sl, 0.3, 4.45, 0.08, 1.15, RED_R)
    txt(sl, "\"Most churn is preventable. Customers tell you they're unhappy — in their complaints, "
        "their calls, their satisfaction scores. The problem is: nobody is reading all those signals together, in real time.\"",
        0.55, 4.55, W-0.9, 1.0, size=13, italic=True, color=WHITE_R)

    # ── Slide 3: STAR — T — Task ──
    sl = blank(prs); bg(sl, NAVY_R)
    rect(sl, 0, 0, W, 1.2, DARK_R)
    rect(sl, 0, 0, 0.1, 1.2, CYAN_R)
    txt(sl, "T", 0.2, 0.1, 0.8, 0.9, size=52, bold=True, color=CYAN_R, align=PP_ALIGN.CENTER)
    txt(sl, "TASK", 1.1, 0.1, 4.0, 0.55, size=30, bold=True, color=WHITE_R)
    txt(sl, "What you actually need to prevent churn", 1.1, 0.65, 9.0, 0.45, size=16, color=ORANGE_R)
    slide_footer(sl)

    needs = [
        ("Know who is leaving\nbefore they do",
         "Not after they've filed a cancellation — weeks before, when you still have time to act."),
        ("Understand WHY,\nnot just who",
         "A risk score with no explanation is useless. Your retention team needs to know the reason to take the right action."),
        ("Prioritise your\nretention effort",
         "You can't call every customer. You need a ranked list: who to call today, who to watch, who is safe."),
        ("Get results without\na data science team",
         "You shouldn't need a PhD to use an AI system. Upload a file. Get results. Take action."),
    ]
    for i, (title, desc) in enumerate(needs):
        col = i % 2; row = i // 2
        x = 0.3 + col * 6.55; y = 1.4 + row * 2.75
        rect(sl, x, y, 6.2, 2.55, BLUE_R)
        rect(sl, x, y, 6.2, 0.55, CYAN_R)
        txt(sl, title, x+0.15, y+0.05, 5.9, 0.5, size=16, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
        txt(sl, desc, x+0.15, y+0.7, 5.9, 1.7, size=13, color=WHITE_R)

    # ── Slide 4: STAR — A — Action (Overview) ──
    sl = blank(prs); bg(sl, NAVY_R)
    rect(sl, 0, 0, W, 1.2, DARK_R)
    rect(sl, 0, 0, 0.1, 1.2, GREEN_R)
    txt(sl, "A", 0.2, 0.1, 0.8, 0.9, size=52, bold=True, color=GREEN_R, align=PP_ALIGN.CENTER)
    txt(sl, "ACTION", 1.1, 0.1, 4.0, 0.55, size=30, bold=True, color=WHITE_R)
    txt(sl, "The Vantive Customer Retention Intelligence Platform", 1.1, 0.65, 10.5, 0.45, size=16, color=CYAN_R)
    slide_footer(sl)

    pipeline = [
        ("1\nUpload", "Your CSV or Excel\nfiles — any format"),
        ("2\nAnalyse", "AI reads complaints,\ncalls, satisfaction"),
        ("3\nScore", "Every customer gets\na churn probability"),
        ("4\nRank", "High / Medium / Low\nrisk tiers assigned"),
        ("5\nExplain", "Top 3 reasons why\neach customer is at risk"),
        ("6\nAct", "Download report.\nCall the right people."),
    ]
    for i, (title, desc) in enumerate(pipeline):
        x = 0.28 + i * 2.15
        rect(sl, x, 1.38, 2.0, 2.75, BLUE_R)
        rect(sl, x, 1.38, 2.0, 0.65, CYAN_R)
        txt(sl, title, x+0.05, 1.39, 1.9, 0.62, size=16, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
        txt(sl, desc, x+0.08, 2.1, 1.85, 1.8, size=12, color=WHITE_R, align=PP_ALIGN.CENTER)
        if i < 5:
            txt(sl, "→", x+1.9, 1.85, 0.35, 0.6, size=22, bold=True, color=ORANGE_R)

    rect(sl, 0.3, 4.35, W-0.6, 1.8, BLUE_R)
    txt(sl, "< 2 minutes from upload to results  ·  No technical knowledge required  ·  Works with your existing data files",
        0.5, 4.45, W-1.0, 0.5, size=14, bold=True, color=ORANGE_R, align=PP_ALIGN.CENTER)
    txt(sl, "The platform automatically maps your column names, handles missing data, reads complaint text, "
        "and scores every customer — you just upload and click.",
        0.5, 5.0, W-1.0, 1.0, size=13, color=WHITE_R, align=PP_ALIGN.CENTER)

    # ── Slide 5: What You Get ──
    sl = blank(prs); bg(sl, NAVY_R)
    slide_header(sl, "What You Get — Every Time You Upload", "Six outputs delivered in under 2 minutes")
    slide_footer(sl)

    deliverables = [
        ("Ranked Risk List", "Every customer scored 0–100%. Highest risk first. No guesswork on where to start."),
        ("Plain-English Reasons", "Not just a number — WHY each customer is at risk. 'Unresolved complaint + 4 calls this month + satisfaction 1.8/5'"),
        ("Retention Recommendations", "A specific suggested action per customer: proactive call, billing resolution, loyalty offer, escalation."),
        ("NuroStudio AI Assistant", "Ask questions in plain English about any customer or segment. Your AI retention advisor, always available."),
        ("PDF + Excel Reports", "Download a formatted summary or 4-sheet workbook instantly. Ready to share with leadership or agents."),
        ("Full Run History", "Every upload saved. Log back in tomorrow, next week, next month — your results are waiting."),
    ]
    for i, (title, desc) in enumerate(deliverables):
        col = i % 2; row = i // 2
        x = 0.3 + col * 6.55; y = 1.35 + row * 1.98
        rect(sl, x, y, 6.2, 1.82, BLUE_R)
        rect(sl, x, y, 0.55, 1.82, CYAN_R)
        txt(sl, str(i+1), x+0.02, y+0.55, 0.52, 0.65, size=22, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
        txt(sl, title, x+0.7, y+0.08, 5.35, 0.5, size=14, bold=True, color=ORANGE_R)
        txt(sl, desc, x+0.7, y+0.62, 5.35, 1.1, size=11, color=WHITE_R)

    # ── Slide 6: NuroStudio ──
    sl = blank(prs); bg(sl, DARK_R)
    rect(sl, 0, 0, W, 1.35, NAVY_R)
    rect(sl, 0, 0, W, 0.1, CYAN_R)
    txt(sl, "NuroStudio", 0.5, 0.12, 6.0, 0.75, size=38, bold=True, color=CYAN_R)
    txt(sl, "Your AI Retention Advisor", 0.5, 0.85, 7.0, 0.42, size=18, color=ORANGE_R)
    txt(sl, "Built into the platform. No extra setup. Ask anything about your customers.",
        7.5, 0.4, 5.5, 0.8, size=13, color=LIGHT_R)
    slide_footer(sl)

    rect(sl, 0.3, 1.5, 5.5, 5.55, NAVY_R)
    txt(sl, "WHAT YOUR TEAM CAN ASK", 0.3, 1.5, 5.5, 0.5, size=13, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
    rect(sl, 0.3, 1.5, 5.5, 0.5, CYAN_R)
    questions = [
        "\"This customer has 87% churn risk —\nwhat should I say when I call them?\"",
        "\"We have 200 high-risk customers.\nWhich segment should we prioritise first?\"",
        "\"What's the most effective retention\noffer for customers disputing a bill?\"",
        "\"Explain why this customer is\nflagged as high risk in plain English.\"",
        "\"What early warning signs should\nwe watch for this quarter?\"",
    ]
    for i, q in enumerate(questions):
        y = 2.15 + i * 0.95
        rect(sl, 0.5, y, 5.1, 0.82, BLUE_R)
        rect(sl, 0.5, y, 0.07, 0.82, ORANGE_R)
        txt(sl, q, 0.65, y+0.08, 4.85, 0.72, size=11, italic=True, color=WHITE_R)

    rect(sl, 6.1, 1.5, 6.9, 5.55, NAVY_R)
    txt(sl, "WHY WE BUILT IT THIS WAY", 6.1, 1.5, 6.9, 0.5, size=13, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
    rect(sl, 6.1, 1.5, 6.9, 0.5, CYAN_R)
    why_lines = [
        ("The gap between data and action", ORANGE_R),
        ("Your retention team can see the score.", WHITE_R),
        ("But they don't always know what to do", WHITE_R),
        ("with it. NuroStudio closes that gap.", WHITE_R),
        ("", WHITE_R),
        ("It answers the 'so what?' question.", CYAN_R),
        ("", WHITE_R),
        ("Powered by the same AI behind the", WHITE_R),
        ("world's leading enterprise systems —", WHITE_R),
        ("but trained specifically on utility", WHITE_R),
        ("customer retention context.", WHITE_R),
        ("", WHITE_R),
        ("It remembers your conversation.", ORANGE_R),
        ("It understands your data.", ORANGE_R),
        ("It speaks your team's language.", ORANGE_R),
        ("", WHITE_R),
        ("No training required. No manual.", WHITE_R),
        ("Just ask your question.", WHITE_R),
    ]
    for i, (line, color) in enumerate(why_lines):
        txt(sl, line, 6.3, 2.15 + i*0.29, 6.6, 0.3, size=11, color=color)

    # ── Slide 7: Accuracy & Improving Over Time ──
    sl = blank(prs); bg(sl, NAVY_R)
    slide_header(sl, "Accuracy — And How It Gets Better Over Time", "What the model does on day one vs. after your data trains it")
    slide_footer(sl)

    rect(sl, 0.3, 1.35, 5.9, 5.7, BLUE_R)
    txt(sl, "DAY ONE", 0.3, 1.35, 5.9, 0.55, size=18, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
    txt(sl, "Ready immediately", 0.3, 1.88, 5.9, 0.38, size=12, color=CYAN_R, align=PP_ALIGN.CENTER)
    rect(sl, 0.3, 1.35, 5.9, 0.55, CYAN_R)
    day1 = [
        "Platform works from your first upload.",
        "No historical data required.",
        "Pre-trained on utility industry patterns.",
        "",
        "Identifies: new customers, frequent",
        "callers, unresolved complaints, very",
        "negative complaint sentiment.",
        "",
        "These signals work across virtually",
        "every utility company — they are",
        "universal churn predictors.",
        "",
        "ROC AUC: 0.83 · Accuracy: 80%",
        "on independent test data.",
        "",
        "Use it today. Start saving customers.",
    ]
    for i, line in enumerate(day1):
        bold = "ROC" in line or "Use it" in line
        color = ORANGE_R if bold else WHITE_R
        txt(sl, line, 0.5, 2.4 + i*0.29, 5.5, 0.3, size=11, bold=bold, color=color)

    rect(sl, 6.5, 1.35, 6.5, 5.7, BLUE_R)
    txt(sl, "AFTER YOUR DATA", 6.5, 1.35, 6.5, 0.55, size=18, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
    txt(sl, "Retrained on your customers", 6.5, 1.88, 6.5, 0.38, size=12, color=ORANGE_R, align=PP_ALIGN.CENTER)
    rect(sl, 6.5, 1.35, 6.5, 0.55, ORANGE_R)
    after = [
        "Upload historical data with a column",
        "showing which customers actually left.",
        "",
        "The platform retrains entirely on",
        "YOUR customer base — learning your",
        "specific market, tariff structure,",
        "and customer demographics.",
        "",
        "This is Full Analysis mode.",
        "",
        "Typical outcome after 6–12 months:",
        "→ ROC AUC rises to 0.88–0.94",
        "→ Churn reduction of 15–30%",
        "→ Model becomes proprietary",
        "→ Specific to your exact market",
        "",
        "Same approach used by AT&T,",
        "E.ON, and major European utilities.",
    ]
    for i, line in enumerate(after):
        bold = line.startswith("→") or "Full Analysis" in line
        color = CYAN_R if line.startswith("→") else WHITE_R
        txt(sl, line, 6.7, 2.4 + i*0.29, 6.1, 0.3, size=11, bold=bold, color=color)

    # ── Slide 8: STAR — R — Results / ROI ──
    sl = blank(prs); bg(sl, NAVY_R)
    rect(sl, 0, 0, W, 1.2, DARK_R)
    rect(sl, 0, 0, 0.1, 1.2, ORANGE_R)
    txt(sl, "R", 0.2, 0.1, 0.8, 0.9, size=52, bold=True, color=ORANGE_R, align=PP_ALIGN.CENTER)
    txt(sl, "RESULT", 1.1, 0.1, 4.0, 0.55, size=30, bold=True, color=WHITE_R)
    txt(sl, "What you can expect when you act on the intelligence", 1.1, 0.65, 10.5, 0.45, size=16, color=CYAN_R)
    slide_footer(sl)

    kpis = [
        ("15–30%", "reduction in annual\nchurn rate"),
        ("10×", "cheaper to retain\nthan replace"),
        ("60–90", "days to break even\nafter deployment"),
        ("< 2 min", "time from upload\nto first results"),
    ]
    for i, (num, label) in enumerate(kpis):
        x = 0.3 + i * 3.25; y = 1.38
        rect(sl, x, y, 3.0, 2.2, BLUE_R)
        txt(sl, num, x+0.1, y+0.2, 2.8, 0.9, size=36, bold=True, color=ORANGE_R, align=PP_ALIGN.CENTER)
        txt(sl, label, x+0.1, y+1.2, 2.8, 0.85, size=13, color=WHITE_R, align=PP_ALIGN.CENTER)

    rect(sl, 0.3, 3.82, W-0.6, 2.0, BLUE_R)
    txt(sl, "ROI EXAMPLE — 50,000 customer utility", 0.5, 3.9, W-1.0, 0.45, size=14, bold=True, color=CYAN_R)
    roi_rows = [
        ("Current churn (20%)", "10,000 customers lost · $12M revenue lost per year"),
        ("Prevent 10% of churn", "1,000 customers saved · $1.2M revenue retained"),
        ("Cost of retention effort", "$50 per customer × 1,000 = $50,000"),
        ("Net return", "$1,150,000 · 2,300% ROI"),
    ]
    for i, (k, v) in enumerate(roi_rows):
        y = 4.45 + i * 0.32
        color = ORANGE_R if "Net return" in k else WHITE_R
        bold = "Net return" in k
        txt(sl, f"{k}:   {v}", 0.6, y, W-1.2, 0.3, size=12, bold=bold, color=color)

    # ── Slide 9: Validation ──
    sl = blank(prs); bg(sl, NAVY_R)
    slide_header(sl, "How You Know It's Working", "Six validation checks — no trust required, just results")
    slide_footer(sl)

    checks = [
        ("Risk Score Distribution", "High-risk customers should represent 15–25% of your base. If it's 80%, something is wrong. We show you this upfront."),
        ("Business Sense Check", "We give you the top 20 High Risk customers. Your best retention manager reviews them. Do they match your intuition? They should."),
        ("Accuracy on Your Data", "If you have historical churn records, the platform shows you precision — of customers it flagged High Risk, how many actually left."),
        ("Lift Analysis", "Customers in the top 20% risk tier should churn 3–5× more than customers in the bottom 20%. We calculate this for you."),
        ("Retrain & Compare", "After 6 months, upload fresh data. Retrain. The accuracy score should go up — that proves the model is learning your market."),
        ("ROI Track", "Track how many High Risk customers your team called and what % were retained. This is the business proof of the whole system."),
    ]
    for i, (title, desc) in enumerate(checks):
        col = i % 2; row = i // 2
        x = 0.3 + col * 6.55; y = 1.35 + row * 1.95
        rect(sl, x, y, 6.2, 1.78, BLUE_R)
        rect(sl, x, y, 6.2, 0.5, CYAN_R)
        txt(sl, title, x+0.15, y+0.05, 5.9, 0.42, size=14, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
        txt(sl, desc, x+0.15, y+0.62, 5.9, 1.05, size=11, color=WHITE_R)

    # ── Slide 10: Why Vantive ──
    sl = blank(prs); bg(sl, DARK_R)
    rect(sl, 0, 0, W, 1.2, NAVY_R)
    rect(sl, 0, 0, W, 0.1, ORANGE_R)
    txt(sl, "Why Vantive", 0.5, 0.15, 7.0, 0.75, size=36, bold=True, color=WHITE_R)
    txt(sl, "What makes this different from building it yourself or buying enterprise software",
        0.5, 0.78, 11.0, 0.38, size=14, color=CYAN_R)
    slide_footer(sl)

    differentiators = [
        ("Ready in minutes,\nnot months",
         "No integration project. No consultant. No waiting. Upload a file and get results."),
        ("Built for utility\ncompanies specifically",
         "Not a generic ML platform. Every feature — complaint severity, autopay impact, SAP IS-U data structure — is designed for your industry."),
        ("No lock-in",
         "Your data is yours. Export at any time. The platform works with the files you already have."),
        ("Grows with you",
         "Starts accurate on day one. Gets more accurate as your data trains it. The model you own after 12 months is proprietary to your business."),
        ("NuroStudio included",
         "AI assistant built in — not an upsell. Your retention team has a smart advisor available instantly."),
        ("Priced for utility teams,\nnot enterprise budgets",
         "Fraction of the cost of building an in-house ML team or buying a full enterprise analytics suite."),
    ]
    for i, (title, desc) in enumerate(differentiators):
        col = i % 3; row = i // 3
        x = 0.28 + col * 4.35; y = 1.35 + row * 2.65
        rect(sl, x, y, 4.1, 2.45, NAVY_R)
        rect(sl, x, y, 0.08, 2.45, CYAN_R)
        txt(sl, title, x+0.2, y+0.1, 3.75, 0.7, size=14, bold=True, color=ORANGE_R)
        txt(sl, desc, x+0.2, y+0.85, 3.75, 1.5, size=11, color=WHITE_R)

    # ── Slide 11: Next Steps / CTA ──
    sl = blank(prs); bg(sl, DARK_R)
    rect(sl, 0, 0, W, 0.12, CYAN_R); rect(sl, 0, H-0.12, W, 0.12, CYAN_R)
    rect(sl, 0, 0.12, W, 2.15, NAVY_R)
    txt(sl, "Ready to See It on Your Data?", 0.6, 0.25, W-1.2, 0.85,
        size=36, bold=True, color=WHITE_R, align=PP_ALIGN.CENTER)
    txt(sl, "Free trial — upload up to 5,000 customers. Results in under 2 minutes. No commitment.",
        0.6, 1.1, W-1.2, 0.6, size=18, color=CYAN_R, align=PP_ALIGN.CENTER)
    rect(sl, 2.0, 2.5, 9.33, 0.07, ORANGE_R)

    steps_next = [
        ("1", "Register", "Create your free account in 60 seconds."),
        ("2", "Upload", "Drop your customer CSV or Excel file."),
        ("3", "Get Results", "Risk scores, reasons, recommendations — in 2 minutes."),
        ("4", "Take Action", "Give your retention team the High Risk list. Start saving customers today."),
    ]
    for i, (num, title, desc) in enumerate(steps_next):
        x = 0.5 + i * 3.1; y = 2.75
        rect(sl, x, y, 2.85, 2.8, BLUE_R)
        rect(sl, x, y, 2.85, 0.55, CYAN_R)
        txt(sl, num, x, y+0.03, 2.85, 0.52, size=24, bold=True, color=NAVY_R, align=PP_ALIGN.CENTER)
        txt(sl, title, x+0.1, y+0.65, 2.65, 0.5, size=16, bold=True, color=ORANGE_R, align=PP_ALIGN.CENTER)
        txt(sl, desc, x+0.1, y+1.2, 2.65, 1.3, size=12, color=WHITE_R, align=PP_ALIGN.CENTER)

    rect(sl, 1.5, 5.85, 10.33, 1.25, NAVY_R)
    txt(sl, "Raj Konka  ·  Vantive Inc.", 1.8, 5.92, 9.5, 0.5,
        size=18, bold=True, color=WHITE_R, align=PP_ALIGN.CENTER)
    txt(sl, "raj.konka@vantiveinc.com  ·  konkarajkumar12@gmail.com",
        1.8, 6.42, 9.5, 0.45, size=14, color=CYAN_R, align=PP_ALIGN.CENTER)

    prs.save(path)
    print(f"[4/4] Client PPTX: {path}")


# ── Run all ───────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating client materials...\n")
    build_internal_pdf()
    build_client_pdf()
    build_internal_pptx()
    build_client_pptx()
    print(f"\n✓ All 4 files saved to: {OUT}")
