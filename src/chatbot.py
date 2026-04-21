"""
Retention Chatbot — NuroStudio + Claude with zero-hallucination guardrails.

Architecture:
  1. NuroStudio API (primary) — context injected into input_value
  2. Claude API (fallback)    — tight system prompt + injected data
  3. Offline mode (last resort) — keyword matching on real data only

Zero-hallucination contract:
  - AI only sees data we explicitly inject from the ML model
  - If data is missing, AI is instructed to ask for it — not invent it
  - System prompt forbids estimation, assumption, or invention of any metric
  - Customer lookups verify existence BEFORE sending to AI
"""

import os
import sys
import json
import re
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

NUROSTUDIO_API_URL = os.environ.get(
    "NUROSTUDIO_API_URL",
    "https://nurostudio.ai/api/v1/run/0da47a3f-d469-406a-8cd9-735a1caeaef8",
)
NUROSTUDIO_API_KEY = os.environ.get("NUROSTUDIO_API_KEY", "")
MAX_INPUT_CHARS    = 5000


# ── System prompt — shared by both NuroStudio and Claude ─────
# This is the contract. Every rule here is enforced by wording, not trust.
_SYSTEM_PROMPT = """You are a customer retention analyst assistant for a utility company churn prediction platform built by Vantive Inc.

YOUR ONLY JOB:
Help retention teams understand and act on the churn predictions produced by the ML model. Nothing else.

═══════════════════════════════════════════════
STRICT RULES — NEVER BREAK THESE
═══════════════════════════════════════════════

RULE 1 — NO INVENTION
You must NEVER invent, estimate, guess, or assume any customer data, churn probability, complaint count, satisfaction score, sentiment score, risk flag, or any metric.
If the data is not in the CONTEXT block below, you do not know it. Say so explicitly.

RULE 2 — NO CUSTOMER WITHOUT DATA
If a user asks about a specific customer and that customer's data is NOT provided in the CONTEXT block, respond exactly:
"I don't have [customer ID]'s data in the current session. Please make sure they are included in your uploaded dataset and run the scoring again."
Never attempt to answer a customer-specific question without their actual data.

RULE 3 — NO DATA = ASK FOR IT
If the user asks something that requires data not in the CONTEXT block, respond with a specific question about what they need to provide. Example:
"To answer that, I need your complaint records uploaded. Do you have a complaints CSV you can add to the upload?"
Never say "typically" or "usually" or "in most cases" as a substitute for real data.

RULE 4 — NO HALLUCINATED STATISTICS
Never quote industry benchmarks, percentages, or statistics that are not in the CONTEXT block. If the user asks "what is a normal churn rate?", you may answer that general knowledge question — but NEVER apply it to their specific data unless their actual churn rate is in the CONTEXT block.

RULE 5 — STAY IN SCOPE
You only answer questions about:
- Customer churn risk from the uploaded dataset
- What specific risk flags mean and why they matter
- Retention actions for specific customers whose data you have
- How the churn prediction model works (explain it, don't re-run it)
- What data the user needs to upload to get better answers

If asked anything outside this scope (general business strategy, pricing, unrelated advice), say:
"That's outside what I can help with in this platform. I'm here to help you understand and act on your customer churn predictions."

RULE 6 — UNCERTAINTY IS HONEST
If you are unsure, say "I'm not certain — here's what I can see in your data: [state only what is in CONTEXT]."
Never fill uncertainty with plausible-sounding content.

═══════════════════════════════════════════════
TONE
═══════════════════════════════════════════════
- Direct and concise. Retention teams are busy.
- Action-oriented. Always end with what the team should DO.
- Never pad responses with disclaimers or filler sentences.
- Use bullet points for recommendations, not paragraphs.
"""


def _build_context(predictor, customer_id=None, message_lower=""):
    """
    Build a structured context block from real ML model data.
    This is ALL the AI is allowed to reference. Nothing else.
    """
    lines = ["═══════════════════════════════════════════════"]
    lines.append("CONTEXT — DATA FROM ML MODEL (use only this)")
    lines.append("═══════════════════════════════════════════════")

    if predictor is None or predictor.merged_data is None:
        lines.append("STATUS: No customer data loaded in this session.")
        lines.append("The user has not uploaded or scored any customer data yet.")
        lines.append("Ask them to upload their customer files and run scoring first.")
        return "\n".join(lines)

    # Dataset summary — always inject
    summary = predictor.get_data_summary()
    lines.append(f"\nDATASET SUMMARY:")
    lines.append(f"  Total customers scored: {summary.get('total_customers', 'N/A'):,}" if isinstance(summary.get('total_customers'), int) else f"  Total customers scored: {summary.get('total_customers', 'N/A')}")
    lines.append(f"  Known churn rate: {summary.get('churn_rate', 'N/A')}")
    lines.append(f"  Average tenure: {summary.get('avg_tenure_months', 'N/A')} months")
    lines.append(f"  Average satisfaction: {summary.get('avg_satisfaction', 'N/A')}/5")
    lines.append(f"  Regions in data: {', '.join(summary.get('regions', [])) or 'N/A'}")
    lines.append(f"  Service types: {', '.join(summary.get('service_types', [])) or 'N/A'}")

    # Risk tier counts — always inject
    try:
        segments = predictor.get_segment_analysis()
        overall  = segments.get("overall", {})
        lines.append(f"\nRISK DISTRIBUTION:")
        lines.append(f"  High Risk  (≥70%): {overall.get('high_risk_count', 'N/A')} customers")
        lines.append(f"  Medium Risk (40–69%): {overall.get('medium_risk_count', 'N/A')} customers")
        lines.append(f"  Low Risk   (<40%): {overall.get('low_risk_count', 'N/A')} customers")
        lines.append(f"  Average churn probability: {overall.get('avg_churn_prob', 'N/A')}")

        # Segment breakdowns
        for seg_key in ["by_region", "by_contract_type", "by_service_type"]:
            seg_data = segments.get(seg_key, {})
            if seg_data:
                label = seg_key.replace("by_", "").replace("_", " ").title()
                lines.append(f"\n{label.upper()} BREAKDOWN:")
                for name, vals in seg_data.items():
                    lines.append(f"  {name}: avg risk {vals.get('avg_churn_prob', 'N/A'):.1%}, {vals.get('customer_count', 'N/A')} customers")
    except Exception:
        lines.append("\nRISK DISTRIBUTION: Could not compute segment analysis.")

    # Top at-risk customers — inject when relevant
    if any(kw in message_lower for kw in ["top", "highest", "most at risk", "worst", "priority", "who should"]):
        try:
            top = predictor.get_top_risk_customers(10)
            lines.append(f"\nTOP 10 HIGHEST RISK CUSTOMERS:")
            for i, c in enumerate(top):
                lines.append(
                    f"  {i+1}. {c.get('customer_id','?')} — "
                    f"{c.get('churn_probability', 0):.1%} risk — "
                    f"{c.get('risk_level','?')} — "
                    f"Region: {c.get('region','N/A')} — "
                    f"Tenure: {c.get('account_tenure_months','N/A')} months"
                )
        except Exception:
            lines.append("\nTOP CUSTOMERS: Could not retrieve.")

    # Specific customer lookup — inject full data if found
    if customer_id:
        lines.append(f"\nSPECIFIC CUSTOMER LOOKUP: {customer_id}")
        try:
            result = predictor.get_retention_recommendations(customer_id)
            if "error" in result:
                lines.append(f"  STATUS: NOT FOUND in current dataset.")
                lines.append(f"  The user asked about {customer_id} but this customer is not in the uploaded data.")
                lines.append(f"  Instruct the AI to tell the user this customer is not in the current session data.")
            else:
                info = result.get("customer_info", {})
                lines.append(f"  Churn probability: {result.get('churn_probability', 'N/A'):.1%}")
                lines.append(f"  Risk level: {result.get('risk_level', 'N/A')}")
                lines.append(f"  Prediction: {result.get('prediction', 'N/A')}")
                lines.append(f"  Name: {info.get('name', 'N/A')}")
                lines.append(f"  Region: {info.get('region', 'N/A')}")
                lines.append(f"  Tenure: {info.get('tenure_months', 'N/A')} months")
                lines.append(f"  Service type: {info.get('service_type', 'N/A')}")
                lines.append(f"  Contract type: {info.get('contract_type', 'N/A')}")
                lines.append(f"  Complaint count: {info.get('complaint_count', 'N/A')}")
                lines.append(f"  Avg sentiment score: {info.get('avg_sentiment_score', 'N/A')} (scale -1 to +1)")
                lines.append(f"  Satisfaction score: {info.get('satisfaction_score', 'N/A')}/5")
                lines.append(f"  Negative sentiment ratio: {info.get('negative_sentiment_ratio', 'N/A')}")
                lines.append(f"  Composite risk score: {info.get('composite_risk_score', 'N/A')}/8")
                recs = result.get("recommendations", [])
                if recs:
                    lines.append(f"  ML-GENERATED RECOMMENDATIONS:")
                    for r in recs:
                        lines.append(f"    [{r['priority']}] {r['action']}: {r['detail']}")
        except Exception as e:
            lines.append(f"  ERROR loading customer data: {e}")

    lines.append("\n═══════════════════════════════════════════════")
    lines.append("END OF CONTEXT — do not reference anything outside the above data.")
    lines.append("═══════════════════════════════════════════════")
    return "\n".join(lines)


def _extract_customer_id(message):
    """Extract a customer ID from the message. Returns None if none found."""
    match = re.search(r'\bCUST\d{4,10}\b|\bC\d{3,6}\b', message.upper())
    return match.group(0) if match else None


class RetentionChatbot:
    def __init__(self, predictor, nuro_key=None, claude_key=None):
        self.predictor = predictor
        self.history   = []

        # Keys passed explicitly from session_state (per-user).
        # Fall back to environment variables only as a last resort
        # (e.g. server-level keys set by the deployment operator).
        self.nuro_key      = nuro_key or os.environ.get("NUROSTUDIO_API_KEY", "") or ""
        self.claude_client = None
        self.mode          = "fallback"

        if self.nuro_key:
            self.mode = "nurostudio"
            print("NuroStudio API ready — zero-hallucination mode active")
        else:
            try:
                import anthropic
                api_key = claude_key or os.environ.get("ANTHROPIC_API_KEY", "") or ""
                if api_key:
                    self.claude_client = anthropic.Anthropic(api_key=api_key)
                    self.mode = "claude"
                    print("Claude API ready — zero-hallucination mode active")
            except ImportError:
                pass

        if self.mode == "fallback":
            print("Offline mode — keyword matching on real data only")

    def get_mode_label(self):
        return {
            "nurostudio": "NuroStudio AI (private)",
            "claude":     "Claude AI (Anthropic)",
            "fallback":   "Offline mode",
        }.get(self.mode, self.mode)

    def chat(self, message):
        """Main entry point. Validates, builds context, routes to backend."""
        if not message or not message.strip():
            return "Please type a question."

        # Truncate oversized input
        if len(message) > MAX_INPUT_CHARS:
            message = message[:MAX_INPUT_CHARS] + "… [message truncated — please shorten your input]"

        message_lower  = message.lower()
        customer_id    = _extract_customer_id(message)
        context_block  = _build_context(self.predictor, customer_id, message_lower)

        if self.mode == "nurostudio":
            return self._nurostudio_response(message, context_block)
        elif self.mode == "claude":
            return self._claude_response(message, context_block)
        else:
            return self._offline_response(message_lower, customer_id)

    # ── NuroStudio ────────────────────────────────────────────

    def _nurostudio_response(self, message, context_block):
        """
        Sends system prompt + context + user message to NuroStudio.
        Context is embedded in the input_value since NuroStudio doesn't
        expose a separate system message field in this API format.
        """
        # Build the full prompt NuroStudio will receive
        full_input = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"{context_block}\n\n"
            f"USER QUESTION: {message}"
        )

        answer = self._call_nurostudio(full_input)
        if answer:
            # Validate: if response looks like it's making something up, flag it
            answer = self._safety_check(answer, context_block)
            self._append_history("user", message)
            self._append_history("assistant", answer)
            return answer

        # NuroStudio failed — fall through to Claude if available, then offline
        if self.claude_client:
            print("NuroStudio unavailable — falling back to Claude")
            return self._claude_response(message, context_block)
        return self._offline_response(message.lower(), _extract_customer_id(message))

    def _call_nurostudio(self, full_prompt):
        try:
            response = requests.post(
                f"{NUROSTUDIO_API_URL}?stream=false",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.nuro_key,
                },
                json={
                    "input_value": full_prompt,
                    "output_type": "chat",
                    "input_type":  "chat",
                },
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                try:
                    return data["outputs"][0]["outputs"][0]["results"]["message"]["text"]
                except (KeyError, IndexError):
                    try:
                        return data["outputs"][0]["outputs"][0]["outputs"]["message"]["message"]
                    except (KeyError, IndexError):
                        return None
            print(f"NuroStudio HTTP {response.status_code}")
            return None
        except requests.exceptions.Timeout:
            print("NuroStudio timeout")
            return None
        except Exception as e:
            print(f"NuroStudio error: {e}")
            return None

    # ── Claude ────────────────────────────────────────────────

    def _claude_response(self, message, context_block):
        """
        Sends a tight system prompt (with rules + context) to Claude.
        History is maintained but capped at 10 turns to avoid drift.
        """
        # System message = rules + current data context
        system_with_context = f"{_SYSTEM_PROMPT}\n\n{context_block}"

        self._append_history("user", message)

        try:
            response = self.claude_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1200,
                system=system_with_context,
                messages=self.history[-10:],  # last 10 turns only
            )
            reply = response.content[0].text
            reply = self._safety_check(reply, context_block)
            self._append_history("assistant", reply)
            return reply
        except Exception as e:
            self.history.pop()  # remove the user message we just added
            return (
                f"The AI assistant is temporarily unavailable ({type(e).__name__}). "
                f"Use the offline commands below:\n\n"
                f"{self._offline_response(message.lower(), _extract_customer_id(message))}"
            )

    # ── Offline mode ──────────────────────────────────────────

    def _offline_response(self, msg_lower, customer_id):
        """
        Pure data lookup — no language model. Zero hallucination by design
        because it only returns values directly from the predictor.
        """
        if self.predictor is None or self.predictor.merged_data is None:
            return (
                "No customer data is loaded yet.\n\n"
                "Please upload your customer files in the **Upload Your Data** tab "
                "and click **Score My Customers** first."
            )

        # Specific customer
        if customer_id:
            result = self.predictor.get_retention_recommendations(customer_id)
            if "error" in result:
                return (
                    f"Customer **{customer_id}** was not found in the current dataset.\n\n"
                    f"Check that this ID exists in your uploaded file."
                )
            return self._format_customer(result)

        # Top risk
        if any(kw in msg_lower for kw in ["top", "highest", "most at risk", "who should i call", "priority"]):
            n = 10
            for word in msg_lower.split():
                try: n = min(int(word), 50); break
                except ValueError: pass
            top = self.predictor.get_top_risk_customers(n)
            if not top:
                return "No customers found. Please upload data first."
            lines = [f"**Top {len(top)} Highest Risk Customers:**\n"]
            for i, c in enumerate(top):
                lines.append(
                    f"{i+1}. **{c.get('customer_id','?')}** — "
                    f"{c.get('churn_probability', 0):.1%} · "
                    f"{c.get('risk_level','?')} · "
                    f"Region: {c.get('region','N/A')}"
                )
            return "\n".join(lines)

        # Summary
        if any(kw in msg_lower for kw in ["summary", "overview", "how many", "total", "dataset"]):
            s = self.predictor.get_data_summary()
            seg = self.predictor.get_segment_analysis().get("overall", {})
            return (
                f"**Dataset Summary:**\n"
                f"- Total customers: {s.get('total_customers', 'N/A'):,}\n"
                f"- Known churn rate: {s.get('churn_rate', 'N/A')}\n"
                f"- High Risk: {seg.get('high_risk_count', 'N/A')}\n"
                f"- Medium Risk: {seg.get('medium_risk_count', 'N/A')}\n"
                f"- Low Risk: {seg.get('low_risk_count', 'N/A')}\n"
                f"- Avg tenure: {s.get('avg_tenure_months', 'N/A')} months\n"
                f"- Avg satisfaction: {s.get('avg_satisfaction', 'N/A')}/5"
            )

        # Region breakdown
        if "region" in msg_lower:
            seg = self.predictor.get_segment_analysis().get("by_region", {})
            if not seg:
                return "No region data available in the current dataset."
            lines = ["**Churn Risk by Region:**"]
            for region, data in seg.items():
                lines.append(
                    f"- {region}: {data['avg_churn_prob']:.1%} avg risk "
                    f"({data['customer_count']} customers)"
                )
            return "\n".join(lines)

        # Contract type
        if "contract" in msg_lower or "plan" in msg_lower:
            seg = self.predictor.get_segment_analysis().get("by_contract_type", {})
            if not seg:
                return "No contract type data available in the current dataset."
            lines = ["**Churn Risk by Contract Type:**"]
            for ct, data in seg.items():
                lines.append(
                    f"- {ct}: {data['avg_churn_prob']:.1%} avg risk "
                    f"({data['customer_count']} customers)"
                )
            return "\n".join(lines)

        # Default — tell them exactly what they can ask
        return (
            "I can answer the following from your uploaded data:\n\n"
            "- **Specific customer**: *'Tell me about CUST0000042'*\n"
            "- **Top risk list**: *'Show top 10 at-risk customers'*\n"
            "- **Dataset overview**: *'Give me a summary'*\n"
            "- **By region**: *'Churn risk by region'*\n"
            "- **By contract**: *'Churn risk by contract type'*\n\n"
            "_I only answer from your actual uploaded data — I will not guess or estimate._"
        )

    # ── Safety check ─────────────────────────────────────────

    def _safety_check(self, response, context_block):
        """
        Post-generation safety check.
        Flags responses that appear to contain invented customer IDs
        not present in the context block.
        """
        invented_ids = re.findall(r'\bCUST\d{4,10}\b', response.upper())
        for cid in invented_ids:
            if cid not in context_block.upper():
                # AI mentioned a customer ID that wasn't in our injected context
                return (
                    "I can't provide information about that customer — "
                    "they are not in the current session's uploaded data.\n\n"
                    "Please make sure the customer is included in your uploaded file "
                    "and re-run scoring."
                )
        return response

    # ── Helpers ───────────────────────────────────────────────

    def _append_history(self, role, content):
        self.history.append({"role": role, "content": content})
        if len(self.history) > 50:
            self.history = self.history[-50:]

    def _format_customer(self, result):
        info = result.get("customer_info", {})
        recs = result.get("recommendations", [])
        rec_lines = "\n".join(
            f"  - [{r['priority']}] **{r['action']}**: {r['detail']}"
            for r in recs
        ) or "  - No specific actions flagged."

        return (
            f"**{result['customer_id']}**\n"
            f"- Risk: **{result['risk_level']}** — {result.get('churn_probability', 0):.1%} churn probability\n"
            f"- Prediction: {result.get('prediction', 'N/A')}\n"
            f"- Name: {info.get('name', 'N/A')}\n"
            f"- Region: {info.get('region', 'N/A')} · Tenure: {info.get('tenure_months', 'N/A')} months\n"
            f"- Service: {info.get('service_type', 'N/A')} · Contract: {info.get('contract_type', 'N/A')}\n"
            f"- Complaints: {info.get('complaint_count', 'N/A')} · "
            f"Satisfaction: {info.get('satisfaction_score', 'N/A')}/5\n"
            f"- Sentiment: {info.get('avg_sentiment_score', 'N/A')} · "
            f"Negative ratio: {info.get('negative_sentiment_ratio', 'N/A')}\n"
            f"- Composite risk score: {info.get('composite_risk_score', 'N/A')}/8\n\n"
            f"**Recommended Actions:**\n{rec_lines}"
        )

    def clear_history(self):
        self.history = []
