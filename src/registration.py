"""
Registration & Access Gate Module — V3
- Collects name, email, company, phone before upload access
- Stores leads in Google Sheets (via Google Forms webhook)
- Sends email notification on new signup
- Enforces 5,000 customer limit on free tier
- Shows 'Contact Us' for larger datasets
- Persistent accounts with hashed passwords so users can log back in
"""
import streamlit as st
import os
import json
import secrets
import hashlib
import fcntl
import tempfile
import requests
import re
from datetime import datetime

# ─── Configuration ────────────────────────────────────────
FREE_TIER_LIMIT = 5000  # Max customers in uploaded data
CONTACT_EMAIL = "raj.konka@vantiveinc.com"  # Replace with your email
CONTACT_PHONE = "6824053943"  # Replace with your phone

# Google Sheets webhook URL — env var takes priority, falls back to hardcoded URL
GSHEET_WEBHOOK = os.environ.get(
    "GSHEET_WEBHOOK",
    "https://script.google.com/macros/s/AKfycbxUbyz53DSdZJNtIBWN9n-sOK-AJCVCqMikl3FiakYMAI-IgzHIQYp3dzBOdwYE4z8cbg/exec"
)

# Email notification webhook (using formspree.io free tier or similar)
# Set this as environment variable EMAIL_WEBHOOK in Hugging Face Spaces settings
EMAIL_WEBHOOK = os.environ.get("EMAIL_WEBHOOK", "")

# Persistent storage — kept outside data/ which gets wiped by git operations
_STORAGE_DIR  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")
LEADS_FILE    = os.path.join(_STORAGE_DIR, "leads.json")
ACCOUNTS_FILE = os.path.join(_STORAGE_DIR, "accounts.json")


# ─── Account helpers ─────────────────────────────────────

def _hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return key.hex(), salt

def _load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    try:
        with open(ACCOUNTS_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def _save_accounts(accounts):
    os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)
    lock_path = ACCOUNTS_FILE + ".lock"
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            with tempfile.NamedTemporaryFile("w", dir=os.path.dirname(ACCOUNTS_FILE), delete=False, suffix=".tmp") as tmp:
                json.dump(accounts, tmp, indent=2)
                tmp_path = tmp.name
            os.replace(tmp_path, ACCOUNTS_FILE)
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)

def _get_account(email):
    for acc in _load_accounts():
        if acc.get("email") == email.strip().lower():
            return acc
    return None

def _create_account(user_info, password):
    """Create a new account. Returns False if email already exists."""
    if _get_account(user_info["email"]):
        return False
    pw_hash, salt = _hash_password(password)
    account = {
        **user_info,
        "password_hash": pw_hash,
        "password_salt": salt,
        "session_id": secrets.token_hex(16),   # permanent — maps to data dir
        "registered_at": datetime.now().isoformat(),
        "last_login": datetime.now().isoformat(),
    }
    accounts = _load_accounts()
    accounts.append(account)
    _save_accounts(accounts)
    return account

def _verify_login(email, password):
    """Verify credentials. Returns account dict on success, None on failure."""
    account = _get_account(email)
    if not account:
        return None
    expected_hash, _ = _hash_password(password, account["password_salt"])
    if not secrets.compare_digest(expected_hash, account["password_hash"]):
        return None
    # Update last_login
    accounts = _load_accounts()
    for acc in accounts:
        if acc["email"] == email.strip().lower():
            acc["last_login"] = datetime.now().isoformat()
    _save_accounts(accounts)
    return account


def is_registered():
    """Check if current session user is registered."""
    return st.session_state.get("user_registered", False)


def get_user_info():
    """Get registered user info from session."""
    return st.session_state.get("user_info", {})


def _apply_login(account):
    """Write account into session state and restore the user's permanent session_id."""
    st.session_state.user_registered = True
    st.session_state.user_info = {k: v for k, v in account.items()
                                   if k not in ("password_hash", "password_salt")}
    st.session_state.session_id = account["session_id"]


def render_registration_gate():
    """
    Show Register / Sign In tabs. Returns True if user is authenticated.
    Call this at the top of the upload tab.
    """
    if is_registered():
        return True

    st.markdown("""
    <div style="text-align: center; padding: 30px 20px; background: linear-gradient(135deg, #f0f4ff 0%, #e8ecf8 100%);
                border-radius: 12px; margin: 10px 0 20px 0;">
        <h3 style="color: #0f3460; margin: 0 0 8px 0;">🔐 Access Required</h3>
        <p style="color: #555; font-size: 14px; margin: 0;">
            Register once to unlock data upload — or sign in if you've been here before.
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_register, tab_signin = st.tabs(["✨ New here? Register", "🔑 Returning? Sign In"])

    # ── Register ──────────────────────────────────────────
    with tab_register:
        with st.form("registration_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                name    = st.text_input("Full Name *", placeholder="John Smith")
                email   = st.text_input("Business Email *", placeholder="john@company.com")
                password = st.text_input("Password *", type="password", placeholder="Min 8 characters")
            with col2:
                company  = st.text_input("Company Name *", placeholder="Acme Utilities Inc.")
                phone    = st.text_input("Phone Number *", placeholder="+1 555-123-4567")
                password2 = st.text_input("Confirm Password *", type="password")

            agree = st.checkbox("I agree to be contacted about this product", value=True)
            submitted = st.form_submit_button("🚀 Create Account & Unlock Access", use_container_width=True, type="primary")

            if submitted:
                errors = []
                if not name or len(name.strip()) < 2:
                    errors.append("Please enter your full name")
                if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email.strip()):
                    errors.append("Please enter a valid email address")
                if not company or len(company.strip()) < 2:
                    errors.append("Please enter your company name")
                if not phone or len(re.sub(r'\D', '', phone)) < 10:
                    errors.append("Please enter a valid phone number (at least 10 digits)")
                if not password or len(password) < 8:
                    errors.append("Password must be at least 8 characters")
                if password != password2:
                    errors.append("Passwords do not match")
                if not agree:
                    errors.append("Please agree to be contacted before continuing")
                if _get_account(email.strip().lower()):
                    errors.append("An account with this email already exists — use Sign In instead")

                if errors:
                    for e in errors: st.error(e)
                else:
                    user_info = {
                        "name":    name.strip(),
                        "email":   email.strip().lower(),
                        "company": company.strip(),
                        "phone":   phone.strip(),
                    }
                    account = _create_account(user_info, password)
                    _save_lead({**user_info, "registered_at": account["registered_at"]})
                    _apply_login(account)
                    st.success(f"✅ Welcome, {name}! Your account is ready.")
                    st.rerun()

    # ── Sign In ───────────────────────────────────────────
    with tab_signin:
        with st.form("signin_form", clear_on_submit=False):
            si_email    = st.text_input("Business Email", placeholder="john@company.com")
            si_password = st.text_input("Password", type="password")
            signin = st.form_submit_button("🔑 Sign In", use_container_width=True, type="primary")

            if signin:
                if not si_email or not si_password:
                    st.error("Please enter your email and password.")
                else:
                    account = _verify_login(si_email.strip().lower(), si_password)
                    if account:
                        _apply_login(account)
                        st.success(f"✅ Welcome back, {account['name']}!")
                        st.rerun()
                    else:
                        st.error("Incorrect email or password.")

    st.markdown("""
    <p style="text-align: center; color: #999; font-size: 11px; margin-top: 10px;">
        Your data is secure. We only use your details to follow up on your interest in the product.
    </p>
    """, unsafe_allow_html=True)

    return False


def check_data_limit(num_customers):
    """
    Check if uploaded data exceeds free tier limit.
    Returns (allowed: bool, message: str)
    """
    if num_customers <= FREE_TIER_LIMIT:
        return True, f"✅ {num_customers:,} customers — within free tier limit ({FREE_TIER_LIMIT:,})"

    return False, None


def render_upgrade_wall(num_customers):
    """Show the 'Contact Us' wall when data exceeds free tier."""
    st.markdown(f"""
    <div style="text-align: center; padding: 30px 20px; background: linear-gradient(135deg, #fff8e1 0%, #fff3cd 100%); 
                border: 2px solid #f39c12; border-radius: 12px; margin: 20px 0;">
        <h3 style="color: #856404; margin: 0 0 10px 0;">📊 Dataset Exceeds Free Tier</h3>
        <p style="color: #856404; font-size: 16px; margin: 0 0 5px 0;">
            Your data has <strong>{num_customers:,} customers</strong> — the free tier supports up to <strong>{FREE_TIER_LIMIT:,}</strong>.
        </p>
        <p style="color: #666; font-size: 14px; margin: 10px 0 20px 0;">
            For enterprise datasets, we offer custom deployment with unlimited customers,<br>
            dedicated infrastructure, and priority support.
        </p>
        <div style="background: white; padding: 20px; border-radius: 8px; display: inline-block; text-align: left;">
            <p style="margin: 0 0 8px 0; color: #333; font-weight: 600;">📞 Contact our team:</p>
            <p style="margin: 0 0 5px 0; color: #555;">Email: <a href="mailto:{CONTACT_EMAIL}" style="color: #667eea;">{CONTACT_EMAIL}</a></p>
            <p style="margin: 0 0 5px 0; color: #555;">Phone: {CONTACT_PHONE}</p>
            <p style="margin: 8px 0 0 0; color: #888; font-size: 12px;">We typically respond within 24 hours</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Also log this as a hot lead
    user_info = get_user_info()
    if user_info:
        lead = {**user_info, "event": "hit_paywall", "customers_attempted": num_customers, "timestamp": datetime.now().isoformat()}
        _save_lead(lead)


def render_contact_form():
    """Render a standalone contact form for enterprise inquiries."""
    st.markdown("### 📞 Contact Us for Enterprise Access")

    with st.form("contact_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name")
            email = st.text_input("Email")
        with col2:
            company = st.text_input("Company")
            phone = st.text_input("Phone")

        dataset_size = st.selectbox("Estimated dataset size", [
            "1,000 - 25,000 customers",
            "25,000 - 100,000 customers",
            "100,000 - 500,000 customers",
            "500,000 - 1 million customers",
            "1 million+ customers",
        ])
        message = st.text_area("Tell us about your needs", placeholder="We are a utility company with 200K customers and want to reduce churn...")

        if st.form_submit_button("Send Inquiry", type="primary", use_container_width=True):
            if name and email and company:
                lead = {
                    "name": name, "email": email, "company": company, "phone": phone,
                    "dataset_size": dataset_size, "message": message,
                    "event": "enterprise_inquiry", "timestamp": datetime.now().isoformat(),
                }
                _save_lead(lead)
                st.success("✅ Thank you! We'll get back to you within 24 hours.")
            else:
                st.error("Please fill in name, email, and company.")


# ─── Backend: Save Leads ──────────────────────────────────

def _save_lead(lead_data):
    """Save lead to all configured backends. Returns True if at least local save succeeded."""
    local_ok = _save_to_local(lead_data)

    if GSHEET_WEBHOOK:
        _save_to_google_sheets(lead_data)

    if EMAIL_WEBHOOK:
        _send_email_notification(lead_data)

    return local_ok


def _save_to_local(lead_data):
    """Save lead to local JSON file with file locking and atomic write."""
    try:
        os.makedirs(os.path.dirname(LEADS_FILE), exist_ok=True)
        lock_path = LEADS_FILE + ".lock"
        with open(lock_path, "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                leads = []
                if os.path.exists(LEADS_FILE):
                    with open(LEADS_FILE, "r") as f:
                        data = json.load(f)
                        leads = data if isinstance(data, list) else []
                leads.append(lead_data)
                dir_name = os.path.dirname(LEADS_FILE)
                with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, suffix=".tmp") as tmp:
                    json.dump(leads, tmp, indent=2)
                    tmp_path = tmp.name
                os.replace(tmp_path, LEADS_FILE)
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
        print(f"  Lead saved locally: {lead_data.get('email', 'unknown')}")
        return True
    except Exception as e:
        print(f"  Warning: Could not save lead locally: {e}")
        return False


def _save_to_google_sheets(lead_data):
    """Send lead data to Google Sheets via Apps Script webhook."""
    try:
        response = requests.post(GSHEET_WEBHOOK, json=lead_data, timeout=10)
        if response.status_code == 200:
            print(f"  Lead saved to Google Sheets: {lead_data.get('email', 'unknown')}")
        else:
            print(f"  Warning: Google Sheets webhook returned {response.status_code}")
    except Exception as e:
        print(f"  Warning: Could not send to Google Sheets: {e}")


def _send_email_notification(lead_data):
    """Send email notification about new lead."""
    try:
        payload = {
            "email": CONTACT_EMAIL,
            "subject": f"New Lead: {lead_data.get('name', 'Unknown')} from {lead_data.get('company', 'Unknown')}",
            "message": (
                f"New registration on SAP IS-U Retention App:\n\n"
                f"Name: {lead_data.get('name', 'N/A')}\n"
                f"Email: {lead_data.get('email', 'N/A')}\n"
                f"Company: {lead_data.get('company', 'N/A')}\n"
                f"Phone: {lead_data.get('phone', 'N/A')}\n"
                f"Event: {lead_data.get('event', 'registration')}\n"
                f"Time: {lead_data.get('registered_at', lead_data.get('timestamp', 'N/A'))}\n"
            ),
        }
        response = requests.post(EMAIL_WEBHOOK, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"  Email notification sent for: {lead_data.get('email', 'unknown')}")
        else:
            print(f"  Warning: Email webhook returned {response.status_code}")
    except Exception as e:
        print(f"  Warning: Could not send email notification: {e}")


def get_lead_stats():
    """Get stats about collected leads (for admin view)."""
    if not os.path.exists(LEADS_FILE):
        return {"total": 0, "registrations": 0, "paywall_hits": 0, "inquiries": 0}

    try:
        with open(LEADS_FILE, "r") as f:
            leads = json.load(f)
        return {
            "total": len(leads),
            "registrations": sum(1 for l in leads if l.get("event") != "hit_paywall" and l.get("event") != "enterprise_inquiry"),
            "paywall_hits": sum(1 for l in leads if l.get("event") == "hit_paywall"),
            "inquiries": sum(1 for l in leads if l.get("event") == "enterprise_inquiry"),
            "leads": leads,
        }
    except Exception:
        return {"total": 0, "registrations": 0, "paywall_hits": 0, "inquiries": 0}
