"""
Universal Data Upload & Mapping Module — V3
Accepts CSV, JSON, Excel, PDF, Word files
Auto-detects column mapping using fuzzy matching
Lets user correct mappings before running pipeline
"""
import pandas as pd
import numpy as np
import os
import sys
import re
import io
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *


# ─── Expected Schemas ─────────────────────────────────────
# What our pipeline expects for each data source
EXPECTED_SCHEMAS = {
    "customer_master": {
        "required": ["customer_id"],
        "optional": [
            "customer_name", "age", "gender", "region", "service_type",
            "contract_type", "dwelling_type", "account_tenure_months",
            "has_autopay", "paperless_billing", "family_size",
            "income_bracket", "home_ownership", "churned",
        ],
        "description": "Customer identity & contract info",
        "keywords": ["customer", "master", "account", "partner", "client", "subscriber", "member"],
    },
    "complaint_data": {
        "required": ["customer_id", "comment"],
        "optional": [
            "complaint_date", "complaint_category", "severity",
            "escalated", "resolved", "resolution_time_days",
        ],
        "description": "Complaints with customer comment text for NLP",
        "keywords": ["complaint", "ticket", "issue", "grievance", "case", "feedback", "comment"],
    },
    "interaction_data": {
        "required": ["customer_id"],
        "optional": [
            "interaction_date", "interaction_type", "channel",
            "duration_minutes", "resolved", "satisfaction_score",
        ],
        "description": "Service interactions — calls, emails, chats",
        "keywords": ["interaction", "contact", "call", "service", "touchpoint", "communication"],
    },
}

# Column name aliases for fuzzy matching
COLUMN_ALIASES = {
    "customer_id": ["customer_id", "cust_id", "customerid", "customer_number", "account_id",
                     "account_number", "partner_id", "client_id", "subscriber_id", "id", "cust_no",
                     "customer id", "account id", "bp_number", "business_partner",
                     "ref", "client_ref", "reference", "account_ref", "customer_ref"],
    "customer_name": ["customer_name", "name", "full_name", "cust_name", "client_name", "account_name"],
    "age": ["age", "customer_age", "years"],
    "gender": ["gender", "sex"],
    "region": ["region", "area", "zone", "territory", "district", "location", "state", "city"],
    "service_type": ["service_type", "service", "utility_type", "product", "product_type"],
    "contract_type": ["contract_type", "contract", "plan", "plan_type", "tariff", "rate_plan", "account_type"],
    "dwelling_type": ["dwelling_type", "dwelling", "property_type", "housing", "residence_type"],
    "account_tenure_months": ["account_tenure_months", "tenure", "tenure_months", "months_active",
                               "customer_since", "account_age", "loyalty_months", "duration"],
    "has_autopay": ["has_autopay", "autopay", "auto_pay", "direct_debit", "automatic_payment"],
    "paperless_billing": ["paperless_billing", "paperless", "ebilling", "digital_billing"],
    "family_size": ["family_size", "household_size", "family_members", "dependents"],
    "income_bracket": ["income_bracket", "income", "income_level", "salary_range"],
    "home_ownership": ["home_ownership", "ownership", "owns_home", "housing_status"],
    "churned": ["churned", "churn", "is_churned", "left", "cancelled", "terminated", "attrition", "status"],
    "comment": ["comment", "comments", "description", "text", "note", "notes", "feedback",
                 "complaint_text", "ticket_description", "issue_description", "message",
                 "customer_comment", "detail", "details", "remark", "remarks", "narrative",
                 "free_text", "verbatim", "complaint_description"],
    "complaint_date": ["complaint_date", "date", "created_date", "ticket_date", "issue_date",
                        "filed_date", "reported_date", "created_at", "timestamp"],
    "complaint_category": ["complaint_category", "category", "type", "complaint_type",
                            "issue_type", "ticket_type", "reason", "topic"],
    "severity": ["severity", "priority", "urgency", "severity_level", "impact", "sev"],
    "escalated": ["escalated", "is_escalated", "escalation", "escalated_flag"],
    "resolved": ["resolved", "is_resolved", "resolution", "status", "closed", "is_closed",
                  "was_resolved"],
    "resolution_time_days": ["resolution_time_days", "resolution_time", "days_to_resolve",
                              "time_to_resolve", "tat", "turnaround", "resolve_days"],
    "interaction_date": ["interaction_date", "date", "contact_date", "call_date", "timestamp", "created_date"],
    "interaction_type": ["interaction_type", "type", "contact_type", "reason", "purpose", "category"],
    "channel": ["channel", "contact_channel", "medium", "source", "method", "communication_channel",
                 "contact_method"],
    "duration_minutes": ["duration_minutes", "duration", "call_duration", "length", "time_spent", "minutes",
                          "call_length_min", "call_length"],
    "satisfaction_score": ["satisfaction_score", "satisfaction", "csat", "rating", "score",
                           "customer_rating", "nps", "feedback_score", "survey_score",
                           "csat_rating"],
}


def read_file(uploaded_file):
    """
    Read any supported file format and return a pandas DataFrame.
    Supports: CSV, TSV, JSON, Excel (xlsx/xls), PDF, Word (docx), TXT
    """
    name = uploaded_file.name.lower()
    content = uploaded_file.read()
    uploaded_file.seek(0)  # Reset for potential re-read

    try:
        # ── CSV / TSV ──
        if name.endswith((".csv", ".tsv")):
            sep = "\t" if name.endswith(".tsv") else ","
            # Try different encodings
            for encoding in ["utf-8", "latin-1", "iso-8859-1", "cp1252"]:
                try:
                    df = pd.read_csv(io.BytesIO(content), sep=sep, encoding=encoding)
                    if len(df.columns) <= 1 and sep == ",":
                        # Maybe semicolon-separated
                        df = pd.read_csv(io.BytesIO(content), sep=";", encoding=encoding)
                    return df, None
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            return None, "Could not decode CSV file with any standard encoding"

        # ── Excel ──
        elif name.endswith((".xlsx", ".xls")):
            try:
                xls = pd.ExcelFile(io.BytesIO(content))
                if len(xls.sheet_names) == 1:
                    df = pd.read_excel(io.BytesIO(content))
                    return df, None
                else:
                    # Multiple sheets — combine or let user choose
                    dfs = {}
                    for sheet in xls.sheet_names:
                        dfs[sheet] = pd.read_excel(io.BytesIO(content), sheet_name=sheet)
                    # Return largest sheet by default
                    largest = max(dfs.keys(), key=lambda k: len(dfs[k]))
                    return dfs[largest], f"Multiple sheets found. Using '{largest}' ({len(dfs[largest])} rows). Sheets: {', '.join(xls.sheet_names)}"
            except Exception as e:
                return None, f"Excel read error: {e}"

        # ── JSON ──
        elif name.endswith(".json"):
            try:
                data = pd.read_json(io.BytesIO(content))
                return data, None
            except ValueError:
                # Try line-delimited JSON
                try:
                    data = pd.read_json(io.BytesIO(content), lines=True)
                    return data, None
                except Exception:
                    # Try loading as dict
                    import json
                    raw = json.loads(content.decode("utf-8"))
                    if isinstance(raw, list):
                        return pd.DataFrame(raw), None
                    elif isinstance(raw, dict):
                        # Check for nested data
                        for key, val in raw.items():
                            if isinstance(val, list):
                                return pd.DataFrame(val), f"Extracted from key: '{key}'"
                        return pd.DataFrame([raw]), None
                    return None, "Unsupported JSON structure"

        # ── PDF ──
        elif name.endswith(".pdf"):
            try:
                import pdfplumber
                tables = []
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    for page in pdf.pages:
                        page_tables = page.extract_tables()
                        for table in page_tables:
                            if table and len(table) > 1:
                                df = pd.DataFrame(table[1:], columns=table[0])
                                tables.append(df)
                    # If no tables found, try text extraction
                    if not tables:
                        text_lines = []
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                text_lines.extend(text.strip().split("\n"))
                        if text_lines:
                            # Try to parse as delimited text
                            for sep in ["\t", ",", "|", ";"]:
                                parts = [line.split(sep) for line in text_lines]
                                if all(len(p) == len(parts[0]) and len(p) > 1 for p in parts):
                                    df = pd.DataFrame(parts[1:], columns=parts[0])
                                    return df, "Extracted from PDF text (tab/comma separated)"
                            return None, "PDF contains text but no structured tables. Please convert to CSV first."
                if tables:
                    combined = pd.concat(tables, ignore_index=True)
                    return combined, f"Extracted {len(tables)} table(s) from PDF"
                return None, "No tables found in PDF"
            except ImportError:
                return None, "PDF support requires pdfplumber. Install with: pip install pdfplumber"
            except Exception as e:
                return None, f"PDF extraction error: {e}"

        # ── Word (docx) ──
        elif name.endswith(".docx"):
            try:
                from docx import Document
                doc = Document(io.BytesIO(content))
                tables = []
                for table in doc.tables:
                    rows = []
                    for row in table.rows:
                        rows.append([cell.text.strip() for cell in row.cells])
                    if rows and len(rows) > 1:
                        df = pd.DataFrame(rows[1:], columns=rows[0])
                        tables.append(df)
                if tables:
                    combined = pd.concat(tables, ignore_index=True)
                    return combined, f"Extracted {len(tables)} table(s) from Word document"

                # If no tables, try to parse text as structured data
                text_lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                if text_lines:
                    for sep in ["\t", ",", "|", ";"]:
                        parts = [line.split(sep) for line in text_lines]
                        if all(len(p) == len(parts[0]) and len(p) > 1 for p in parts):
                            df = pd.DataFrame(parts[1:], columns=parts[0])
                            return df, "Extracted from Word document text"
                return None, "No tables found in Word document"
            except ImportError:
                return None, "Word support requires python-docx. Install with: pip install python-docx"
            except Exception as e:
                return None, f"Word extraction error: {e}"

        # ── TXT ──
        elif name.endswith(".txt"):
            text = content.decode("utf-8", errors="replace")
            lines = text.strip().split("\n")
            for sep in ["\t", ",", "|", ";"]:
                parts = [line.split(sep) for line in lines]
                if all(len(p) == len(parts[0]) and len(p) > 1 for p in parts[:10]):
                    df = pd.DataFrame(parts[1:], columns=parts[0])
                    return df, f"Parsed as {sep}-separated text"
            return None, "Could not detect column structure in text file. Please use CSV format."

        else:
            return None, f"Unsupported file format: {name.split('.')[-1]}. Supported: csv, tsv, json, xlsx, xls, pdf, docx, txt"

    except Exception as e:
        return None, f"Error reading file: {e}"


def auto_detect_table_type(df, filename=""):
    """
    Guess which pipeline table this DataFrame maps to based on column names and content.
    Returns: "customer_master", "complaint_data", "interaction_data", or "unknown"
    """
    cols_lower = set(c.lower().strip().replace(" ", "_") for c in df.columns)
    filename_lower = filename.lower()

    scores = {}
    for table_name, schema in EXPECTED_SCHEMAS.items():
        score = 0
        # Check filename keywords
        for kw in schema["keywords"]:
            if kw in filename_lower:
                score += 3
        # Check column matches
        all_expected = schema["required"] + schema["optional"]
        for expected_col in all_expected:
            aliases = COLUMN_ALIASES.get(expected_col, [expected_col])
            for alias in aliases:
                if alias.lower().replace(" ", "_") in cols_lower:
                    score += 2 if expected_col in schema["required"] else 1
                    break
        # Check content patterns
        if table_name == "complaint_data":
            for col in df.columns:
                sample = df[col].dropna().astype(str).head(20)
                avg_len = sample.str.len().mean()
                if avg_len > 30:  # Long text = likely comments
                    score += 3
                    break
        scores[table_name] = score

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def auto_map_columns(df, table_type):
    """
    Auto-map DataFrame columns to expected schema columns using fuzzy matching.
    Returns: {expected_col: detected_col} mapping
    """
    schema = EXPECTED_SCHEMAS.get(table_type, {})
    all_expected = schema.get("required", []) + schema.get("optional", [])
    df_cols = df.columns.tolist()

    mapping = {}
    used_cols = set()

    for expected_col in all_expected:
        aliases = COLUMN_ALIASES.get(expected_col, [expected_col])
        best_match = None
        best_score = 0

        for df_col in df_cols:
            if df_col in used_cols:
                continue
            df_col_clean = df_col.lower().strip().replace(" ", "_").replace("-", "_")

            # Exact alias match
            for alias in aliases:
                if df_col_clean == alias.lower().replace(" ", "_"):
                    best_match = df_col
                    best_score = 1.0
                    break

            if best_score == 1.0:
                break

            # Fuzzy match against aliases
            for alias in aliases:
                score = SequenceMatcher(None, df_col_clean, alias.lower()).ratio()
                if score > best_score and score > 0.6:
                    best_score = score
                    best_match = df_col

            # Check if column name contains the expected name
            if best_score < 0.8:
                for alias in aliases:
                    if alias.lower() in df_col_clean or df_col_clean in alias.lower():
                        if len(df_col_clean) > 2:  # Avoid matching tiny strings
                            best_match = df_col
                            best_score = 0.85
                            break

        if best_match and best_score > 0.5:
            mapping[expected_col] = best_match
            used_cols.add(best_match)

    # Special handling: auto-detect comment column by text length
    if table_type == "complaint_data" and "comment" not in mapping:
        for col in df_cols:
            if col in used_cols:
                continue
            sample = df[col].dropna().astype(str).head(50)
            avg_len = sample.str.len().mean()
            if avg_len > 25:
                mapping["comment"] = col
                used_cols.add(col)
                break

    # Special handling: auto-detect customer_id by pattern
    if "customer_id" not in mapping:
        for col in df_cols:
            if col in used_cols:
                continue
            sample = df[col].dropna().astype(str).head(20)
            # Check for ID-like patterns (alphanumeric, mostly unique)
            unique_ratio = sample.nunique() / len(sample) if len(sample) > 0 else 0
            if unique_ratio > 0.8:
                mapping["customer_id"] = col
                used_cols.add(col)
                break

    return mapping


def transform_dataframe(df, column_mapping, table_type):
    """
    Transform uploaded DataFrame to match expected schema.
    Renames columns, fills defaults, validates data types.
    """
    schema = EXPECTED_SCHEMAS.get(table_type, {})
    
    # Build rename map: {original_col: expected_col}
    rename_map = {v: k for k, v in column_mapping.items()}
    
    # Make a copy and rename
    transformed = df.copy()
    transformed = transformed.rename(columns=rename_map)
    
    # Verify rename worked
    print(f"  [{table_type}] Original cols: {list(df.columns)}")
    print(f"  [{table_type}] Rename map: {rename_map}")
    print(f"  [{table_type}] After rename: {list(transformed.columns)}")
    
    # Keep only recognized columns
    all_expected = schema.get("required", []) + schema.get("optional", [])
    keep_cols = [c for c in all_expected if c in transformed.columns]
    
    # Safety check: ensure required columns exist
    for req in schema.get("required", []):
        if req not in keep_cols:
            print(f"  WARNING: Required column '{req}' missing after transform!")
    
    transformed = transformed[keep_cols]

    # Fill defaults for missing optional columns
    defaults = {
        "customer_name": "Unknown",
        "age": 45,
        "gender": "Unknown",
        "region": "Unknown",
        "service_type": "Electricity",
        "contract_type": "Residential",
        "dwelling_type": "Unknown",
        "account_tenure_months": 24,
        "has_autopay": 0,
        "paperless_billing": 0,
        "family_size": 2,
        "income_bracket": "Medium",
        "home_ownership": "Unknown",
        "churned": 0,
        "complaint_date": "2024-06-01",
        "complaint_category": "General",
        "severity": 3,
        "escalated": 0,
        "resolved": 1,
        "resolution_time_days": 3,
        "interaction_date": "2024-06-01",
        "interaction_type": "General Inquiry",
        "channel": "Phone",
        "duration_minutes": 5,
        "satisfaction_score": 3,
    }

    for col in all_expected:
        if col not in transformed.columns and col in defaults:
            transformed[col] = defaults[col]

    # Data type validation
    int_cols = ["age", "severity", "escalated", "resolved", "resolution_time_days",
                "duration_minutes", "satisfaction_score", "has_autopay", "paperless_billing",
                "family_size", "churned", "account_tenure_months"]
    for col in int_cols:
        if col in transformed.columns:
            transformed[col] = pd.to_numeric(transformed[col], errors="coerce").fillna(defaults.get(col, 0)).astype(int)

    if "severity" in transformed.columns:
        transformed["severity"] = transformed["severity"].clip(1, 5)
    if "satisfaction_score" in transformed.columns:
        transformed["satisfaction_score"] = transformed["satisfaction_score"].clip(1, 5)
    if "age" in transformed.columns:
        transformed["age"] = transformed["age"].clip(18, 95)
    
    # Ensure customer_id is string
    if "customer_id" in transformed.columns:
        transformed["customer_id"] = transformed["customer_id"].astype(str).str.strip()

    return transformed

def generate_missing_data(table_type, customer_ids):
    """Generate placeholder data for a table type the user didn't upload."""
    n = len(customer_ids)
    np.random.seed(RANDOM_STATE)

    if table_type == "complaint_data":
        # Generate minimal complaints with neutral comments
        records = []
        for cid in customer_ids:
            n_comp = np.random.choice([0, 1, 2], p=[0.3, 0.4, 0.3])
            for _ in range(n_comp):
                records.append({
                    "customer_id": cid,
                    "complaint_date": "2024-06-01",
                    "complaint_category": "General",
                    "severity": np.random.randint(1, 4),
                    "comment": "General account inquiry, no specific issues noted.",
                    "escalated": 0,
                    "resolved": 1,
                    "resolution_time_days": np.random.randint(1, 5),
                })
        return pd.DataFrame(records) if records else pd.DataFrame(columns=["customer_id", "comment", "severity", "complaint_category", "escalated", "resolved", "resolution_time_days", "complaint_date"])

    elif table_type == "interaction_data":
        records = []
        for cid in customer_ids:
            n_int = np.random.choice([1, 2, 3], p=[0.3, 0.4, 0.3])
            for _ in range(n_int):
                records.append({
                    "customer_id": cid,
                    "interaction_date": "2024-06-01",
                    "interaction_type": "General Inquiry",
                    "channel": np.random.choice(["Phone", "Email", "Web Chat"]),
                    "duration_minutes": np.random.randint(2, 15),
                    "resolved": 1,
                    "satisfaction_score": np.random.randint(2, 5),
                })
        return pd.DataFrame(records)

    elif table_type == "customer_master":
        return pd.DataFrame({
            "customer_id": customer_ids,
            "customer_name": [f"Customer_{i}" for i in range(n)],
            "age": np.random.normal(45, 15, n).clip(18, 85).astype(int),
            "gender": np.random.choice(["Male", "Female"], n),
            "region": np.random.choice(["Northeast", "Southeast", "Midwest", "West"], n),
            "service_type": "Electricity",
            "contract_type": "Residential",
            "dwelling_type": "Unknown",
            "account_tenure_months": np.random.exponential(36, n).clip(1, 120).astype(int),
            "has_autopay": 0,
            "paperless_billing": 0,
            "family_size": 2,
            "income_bracket": "Medium",
            "home_ownership": "Unknown",
        })

    return pd.DataFrame()


def infer_churn_labels(master_df, complaint_df, interaction_df):
    """Infer churn labels from behavioral data when not provided."""
    cid_list = master_df["customer_id"].tolist()
    scores = np.zeros(len(master_df))

    if len(complaint_df) > 0:
        comp = complaint_df.groupby("customer_id").agg(
            n=("severity", "count"), avg_sev=("severity", "mean"),
            n_esc=("escalated", "sum"),
        ).reindex(cid_list).fillna(0)
        scores += (comp["n"].values * 0.04).clip(0, 0.25)
        scores += ((comp["avg_sev"].values - 2.5) * 0.08).clip(0, 0.20)
        scores += (comp["n_esc"].values * 0.06).clip(0, 0.15)

    if len(interaction_df) > 0 and "satisfaction_score" in interaction_df.columns:
        sat = interaction_df.groupby("customer_id")["satisfaction_score"].mean().reindex(cid_list).fillna(3)
        scores += ((3.0 - sat.values) * 0.08).clip(0, 0.20)

    if "account_tenure_months" in master_df.columns:
        tenure = master_df["account_tenure_months"].values
        scores += np.where(tenure < 6, 0.15, np.where(tenure < 12, 0.08, 0.0))

    np.random.seed(RANDOM_STATE)
    scores += np.random.normal(0, 0.06, len(master_df))
    prob = 1 / (1 + np.exp(-8 * (scores - 0.30)))
    return (np.random.random(len(master_df)) < prob).astype(int)
