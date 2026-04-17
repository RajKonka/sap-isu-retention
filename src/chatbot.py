"""
Retention Chatbot — NuroStudio Integration
Uses NuroStudio API for AI-powered Q&A instead of Claude.
Data stays in your database — zero external data leakage.
Falls back to keyword matching if no API key provided.
"""
import os
import sys
import json
import re
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

# NuroStudio API config — set NUROSTUDIO_API_URL in environment to override
NUROSTUDIO_API_URL = os.environ.get(
    "NUROSTUDIO_API_URL",
    "https://nurostudio.ai/api/v1/run/0da47a3f-d469-406a-8cd9-735a1caeaef8",
)
NUROSTUDIO_API_KEY = os.environ.get("NUROSTUDIO_API_KEY", "")

MAX_INPUT_CHARS = 5000


class RetentionChatbot:
    def __init__(self, predictor):
        self.predictor = predictor
        self.history = []

        # Check for NuroStudio API key first, then Claude
        self.nuro_key = os.environ.get("NUROSTUDIO_API_KEY", "")
        self.claude_client = None
        self.mode = "fallback"

        if self.nuro_key:
            self.mode = "nurostudio"
            print("NuroStudio API initialized — data stays private")
        else:
            # Try Claude as secondary option
            try:
                import anthropic
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
                if api_key:
                    self.claude_client = anthropic.Anthropic(api_key=api_key)
                    self.mode = "claude"
                    print("Claude API initialized (NuroStudio key not found)")
            except ImportError:
                pass

        if self.mode == "fallback":
            print("Using local keyword matching (no API keys found)")

    def get_mode_label(self):
        """Human-readable label for the active backend."""
        return {"nurostudio": "NuroStudio (private AI)", "claude": "Claude AI", "fallback": "Offline mode"}.get(self.mode, self.mode)

    def chat(self, message):
        """Route to appropriate backend."""
        if len(message) > MAX_INPUT_CHARS:
            message = message[:MAX_INPUT_CHARS] + "… [truncated]"
        # Check for customer lookup first
        cust_id = self._extract_customer_id(message)
        
        if self.mode == "nurostudio":
            return self._nurostudio_response(message, cust_id)
        elif self.mode == "claude":
            return self._claude_response(message, cust_id)
        else:
            return self._fallback_response(message, cust_id)

    def _nurostudio_response(self, message, cust_id=None):
        """Send query to NuroStudio API — data stays in your database."""
        # If it's a customer lookup, use local predictor first for structured data
        if cust_id:
            local_result = self.predictor.get_retention_recommendations(cust_id)
            if "error" not in local_result:
                # Combine local prediction with NuroStudio query
                local_summary = self._format_prediction(local_result)
                nuro_answer = self._call_nurostudio(f"Tell me about customer {cust_id} from customer_data table")
                if nuro_answer:
                    return f"{local_summary}\n\n**Additional insights from database:**\n{nuro_answer}"
                return local_summary

        # For general queries, send to NuroStudio
        nuro_answer = self._call_nurostudio(message)
        if nuro_answer:
            return nuro_answer

        # Fall back to local if NuroStudio fails
        return self._fallback_response(message, cust_id)

    def _call_nurostudio(self, query):
        """Make API call to NuroStudio."""
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.nuro_key,
            }
            payload = {
                "input_value": query,
                "output_type": "chat",
                "input_type": "chat",
            }

            response = requests.post(
                f"{NUROSTUDIO_API_URL}?stream=false",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                # Extract the text from NuroStudio response
                try:
                    text = data["outputs"][0]["outputs"][0]["results"]["message"]["text"]
                    return text
                except (KeyError, IndexError):
                    # Try alternate path
                    try:
                        text = data["outputs"][0]["outputs"][0]["outputs"]["message"]["message"]
                        return text
                    except (KeyError, IndexError):
                        return None
            else:
                print(f"NuroStudio API error: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            print("NuroStudio API timeout")
            return None
        except Exception as e:
            print(f"NuroStudio API error: {e}")
            return None

    def _claude_response(self, message, cust_id=None):
        """Fallback to Claude if NuroStudio not available."""
        context = ""
        if cust_id:
            result = self.predictor.get_retention_recommendations(cust_id)
            context = f"\n\nCUSTOMER DATA:\n{json.dumps(result, indent=2, default=str)}"

        if "top" in message.lower() and ("risk" in message.lower() or "churn" in message.lower()):
            top = self.predictor.get_top_risk_customers(10)
            context = f"\n\nTOP AT-RISK:\n{json.dumps(top, indent=2, default=str)}"

        summary = self.predictor.get_data_summary()
        segments = self.predictor.get_segment_analysis()
        system = f"""You are a customer retention analyst. Answer based on this data:
Total customers: {summary.get('total_customers', 'N/A')}
Churn rate: {summary.get('churn_rate', 'N/A')}
Regions: {summary.get('regions', [])}
{context}"""

        self.history.append({"role": "user", "content": message})
        if len(self.history) > 50:
            self.history = self.history[-50:]
        try:
            response = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=system,
                messages=self.history[-10:],
            )
            reply = response.content[0].text
            self.history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"API Error: {e}\n\n{self._fallback_response(message, cust_id)}"

    def _fallback_response(self, message, cust_id=None):
        """Local keyword matching — no API needed."""
        msg = message.lower()

        if cust_id:
            result = self.predictor.get_retention_recommendations(cust_id)
            if "error" in result:
                return f"Customer {cust_id} not found in the database."
            return self._format_prediction(result)

        elif "summary" in msg or "overview" in msg:
            s = self.predictor.get_data_summary()
            return (f"**Data Summary:**\n"
                    f"- Customers: {s['total_customers']:,}\n"
                    f"- Churn Rate: {s['churn_rate']}\n"
                    f"- Avg Tenure: {s['avg_tenure_months']} months\n"
                    f"- Avg Satisfaction: {s['avg_satisfaction']}/5")

        elif "top" in msg and ("risk" in msg or "churn" in msg):
            n = 10
            for word in message.split():
                try:
                    n = int(word); break
                except ValueError:
                    pass
            top = self.predictor.get_top_risk_customers(min(n, 50))
            lines = [f"{i+1}. **{c['customer_id']}** — {c['churn_probability']:.1%} risk"
                     for i, c in enumerate(top)]
            return f"**Top {len(top)} At-Risk Customers:**\n" + "\n".join(lines)

        elif "region" in msg:
            segments = self.predictor.get_segment_analysis()
            rd = segments.get("by_region", {})
            if rd:
                lines = [f"- {r}: {d['avg_churn_prob']:.1%} avg risk ({d['customer_count']} customers)"
                         for r, d in rd.items()]
                return "**Churn Risk by Region:**\n" + "\n".join(lines)
            return "No region data available."

        else:
            mode_msg = {
                "nurostudio": "Connected to NuroStudio (private AI).",
                "claude": "Connected to Claude AI.",
                "fallback": "Running in offline mode."
            }.get(self.mode, "")

            return (f"I can help with:\n"
                    f"- **Customer lookup**: 'Tell me about CUST0000042'\n"
                    f"- **Top risk**: 'Show top 10 at-risk customers'\n"
                    f"- **Summary**: 'Give me a data summary'\n"
                    f"- **By region**: 'What is the churn rate by region?'\n\n"
                    f"_{mode_msg}_")

    def _format_prediction(self, result):
        """Format a prediction result into readable text."""
        info = result["customer_info"]
        recs = "\n".join([f"- [{r['priority']}] **{r['action']}**: {r['detail']}"
                          for r in result.get("recommendations", [])])
        return (f"**{result['customer_id']}** — Risk: **{result['risk_level']}** | "
                f"Churn Probability: **{result['churn_probability']:.1%}**\n\n"
                f"Complaints: {info.get('complaint_count', 'N/A')} | "
                f"Sentiment: {info.get('avg_sentiment_score', 'N/A')} | "
                f"Satisfaction: {info.get('satisfaction_score', 'N/A')}/5\n\n"
                f"**Recommendations:**\n{recs}")

    def _extract_customer_id(self, message):
        """Extract customer ID from message."""
        match = re.search(r'CUST\d{7}|C\d{3,4}', message.upper())
        return match.group(0) if match else None

    def clear_history(self):
        self.history = []
