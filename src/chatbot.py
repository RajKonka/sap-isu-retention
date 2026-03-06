"""
Retention Chatbot — V3
AI-powered chatbot using Claude API with keyword fallback.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class RetentionChatbot:
    def __init__(self, predictor):
        self.predictor = predictor
        self.client = None
        self.history = []

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if HAS_ANTHROPIC and api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
            print("Claude API initialized successfully")
        else:
            print("Warning: Using fallback mode (no API key or anthropic package)")

    def _build_system_prompt(self):
        summary = self.predictor.get_data_summary()
        segments = self.predictor.get_segment_analysis()
        return f"""You are an expert SAP IS-U customer retention analyst. You help utility company managers understand churn risk and take action.

DATA CONTEXT:
- Total customers: {summary.get('total_customers', 'N/A')}
- Churn rate: {summary.get('churn_rate', 'N/A')}
- Regions: {summary.get('regions', [])}
- Service types: {summary.get('service_types', [])}
- Avg tenure: {summary.get('avg_tenure_months', 0)} months
- Avg satisfaction: {summary.get('avg_satisfaction', 0)}/5

SEGMENT ANALYSIS:
{json.dumps(segments, indent=2, default=str)}

V3 MODEL: This system uses 3 inputs only — Customer Master, Complaints (with NLP sentiment from VADER), and Interactions. Feature weights may be user-configured.

When asked about a specific customer (e.g. CUST0000001), use the prediction data. Provide actionable retention recommendations. Be specific with numbers."""

    def chat(self, message):
        # Check for customer lookup
        cust_id = self._extract_customer_id(message)
        context = ""
        if cust_id:
            result = self.predictor.get_retention_recommendations(cust_id)
            context = f"\n\nCUSTOMER DATA FOR {cust_id}:\n{json.dumps(result, indent=2, default=str)}"

        if "top" in message.lower() and ("risk" in message.lower() or "churn" in message.lower()):
            n = 10
            for word in message.split():
                try:
                    n = int(word)
                    break
                except ValueError:
                    pass
            top = self.predictor.get_top_risk_customers(min(n, 50))
            context = f"\n\nTOP {len(top)} AT-RISK CUSTOMERS:\n{json.dumps(top, indent=2, default=str)}"

        if self.client:
            return self._claude_response(message, context)
        else:
            return self._fallback_response(message, cust_id, context)

    def _claude_response(self, message, context):
        system = self._build_system_prompt()
        if context:
            system += context

        self.history.append({"role": "user", "content": message})
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=system,
                messages=self.history[-10:],
            )
            reply = response.content[0].text
            self.history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"API Error: {e}\n\nFalling back to local analysis:\n{self._fallback_response(message, None, context)}"

    def _fallback_response(self, message, cust_id, context):
        msg = message.lower()
        if cust_id:
            result = self.predictor.get_retention_recommendations(cust_id)
            if "error" in result:
                return f"Customer {cust_id} not found."
            info = result["customer_info"]
            recs = "\n".join([f"- [{r['priority']}] {r['action']}: {r['detail']}" for r in result.get("recommendations", [])])
            return (f"**{cust_id}** — Risk: **{result['risk_level']}** | "
                    f"Churn Probability: **{result['churn_probability']:.1%}**\n\n"
                    f"Complaints: {info['complaint_count']} | Sentiment: {info['avg_sentiment_score']:.3f} | "
                    f"Satisfaction: {info['satisfaction_score']}/5\n\n"
                    f"**Recommendations:**\n{recs}")
        elif "summary" in msg or "overview" in msg:
            s = self.predictor.get_data_summary()
            return (f"**Data Summary:**\n- Customers: {s['total_customers']:,}\n"
                    f"- Churn Rate: {s['churn_rate']}\n- Avg Tenure: {s['avg_tenure_months']} months\n"
                    f"- Avg Satisfaction: {s['avg_satisfaction']}/5")
        elif "top" in msg and ("risk" in msg or "churn" in msg):
            top = self.predictor.get_top_risk_customers(10)
            lines = [f"{i+1}. **{c['customer_id']}** — {c['churn_probability']:.1%} churn prob" for i, c in enumerate(top)]
            return "**Top 10 At-Risk Customers:**\n" + "\n".join(lines)
        else:
            return ("I can help with:\n- **Customer lookup**: 'Tell me about CUST0000042'\n"
                    "- **Top risk**: 'Show top 10 at-risk customers'\n"
                    "- **Summary**: 'Give me a data summary'\n\n"
                    "For AI-powered responses, add your Anthropic API key in the sidebar.")

    def _extract_customer_id(self, message):
        import re
        match = re.search(r'CUST\d{7}', message.upper())
        return match.group(0) if match else None

    def clear_history(self):
        self.history = []
