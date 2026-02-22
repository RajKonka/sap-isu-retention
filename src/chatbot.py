"""
GenAI Chatbot Module
Uses Anthropic Claude API to provide intelligent Q&A about customer retention.
Combines ML predictions with natural language understanding.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


SYSTEM_PROMPT = """You are an AI-powered Customer Retention Analyst for a utility company using SAP IS-U.
You have access to customer data, churn predictions, and retention insights.

Your role:
1. Answer questions about customer churn risk and retention
2. Provide data-driven insights from the ML model predictions
3. Recommend retention strategies based on customer profiles
4. Explain patterns and trends in customer behavior
5. Help identify at-risk customer segments

When responding:
- Be specific with numbers and data when available
- Provide actionable recommendations
- Reference the ML model's predictions when relevant
- Be clear about what is a prediction vs. observed data
- Format responses clearly with key metrics highlighted

You have the following context about the data and predictions:
{context}

Current query context (if specific to a customer or analysis):
{query_context}
"""


class RetentionChatbot:
    """AI-powered chatbot for customer retention analysis."""

    def __init__(self, predictor):
        self.predictor = predictor
        self.client = None
        self.conversation_history = []

        api_key = os.environ.get("ANTHROPIC_API_KEY", "") or ANTHROPIC_API_KEY
        if HAS_ANTHROPIC and api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
            print("Claude API initialized successfully")
        else:
            if not HAS_ANTHROPIC:
                print("Warning: anthropic package not installed. Using fallback mode.")
            elif not api_key:
                print("Warning: ANTHROPIC_API_KEY not set. Using fallback mode.")
                
    def _build_context(self):
        """Build context string from data summary."""
        summary = self.predictor.get_data_summary()
        segments = self.predictor.get_segment_analysis()
        top_risk = self.predictor.get_top_risk_customers(10)

        context = f"""
DATA SUMMARY:
- Total Customers: {summary['total_customers']}
- Overall Churn Rate: {summary['churn_rate']}
- Regions: {', '.join(summary['regions'])}
- Service Types: {', '.join(summary['service_types'])}
- Average Tenure: {summary['avg_tenure_months']} months
- Average Monthly Bill: ${summary['avg_monthly_bill']}
- Average Satisfaction Score: {summary['avg_satisfaction']}/5

RISK DISTRIBUTION:
- High Risk Customers: {segments.get('overall', {}).get('high_risk_count', 'N/A')}
- Medium Risk Customers: {segments.get('overall', {}).get('medium_risk_count', 'N/A')}
- Low Risk Customers: {segments.get('overall', {}).get('low_risk_count', 'N/A')}

SEGMENT ANALYSIS:
By Region: {json.dumps(segments.get('by_region', {}), indent=2)}
By Contract Type: {json.dumps(segments.get('by_contract_type', {}), indent=2)}
By Service Type: {json.dumps(segments.get('by_service_type', {}), indent=2)}

TOP 10 AT-RISK CUSTOMERS:
{json.dumps(top_risk[:10], indent=2, default=str)}
"""
        return context

    def _get_query_context(self, user_message):
        """Extract customer ID from message and get specific context."""
        # Check if user is asking about a specific customer
        import re
        customer_match = re.search(r"CUST\d{7}", user_message.upper())
        if customer_match:
            cid = customer_match.group()
            prediction = self.predictor.get_retention_recommendations(cid)
            return json.dumps(prediction, indent=2, default=str)
        return "No specific customer referenced."

    def chat(self, user_message):
        """Process a chat message and return response."""
        context = self._build_context()
        query_context = self._get_query_context(user_message)

        if self.client:
            return self._chat_with_claude(user_message, context, query_context)
        else:
            return self._fallback_chat(user_message, context, query_context)

    def _chat_with_claude(self, user_message, context, query_context):
        """Chat using Claude API."""
        system = SYSTEM_PROMPT.format(context=context, query_context=query_context)

        self.conversation_history.append({"role": "user", "content": user_message})

        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2048,
                system=system,
                messages=self.conversation_history[-10:],  # Keep last 10 messages
            )
            assistant_message = response.content[0].text
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            return assistant_message
        except Exception as e:
            return f"API Error: {str(e)}\n\nFalling back to local analysis...\n\n{self._fallback_chat(user_message, context, query_context)}"

    def _fallback_chat(self, user_message, context, query_context):
        """Fallback response when API is not available."""
        msg = user_message.lower()

        # ── Specific customer lookup ──
        import re
        customer_match = re.search(r"cust\d{7}", msg)
        if customer_match:
            cid = customer_match.group().upper()
            result = self.predictor.get_retention_recommendations(cid)
            if "error" in result:
                return f"Customer {cid} not found in the database."
            return self._format_customer_report(result)

        # ── Top risk customers ──
        if any(kw in msg for kw in ["top risk", "highest risk", "at risk", "most likely to churn", "top churn"]):
            top = self.predictor.get_top_risk_customers(10)
            lines = ["**Top 10 At-Risk Customers:**\n"]
            for i, c in enumerate(top, 1):
                lines.append(
                    f"{i}. **{c['customer_id']}** | {c['region']} | "
                    f"Tenure: {c['account_tenure_months']}mo | "
                    f"Churn Prob: **{c['churn_probability']:.1%}** ({c['risk_level']})"
                )
            return "\n".join(lines)

        # ── Segment analysis ──
        if any(kw in msg for kw in ["segment", "region", "breakdown", "analysis", "overview"]):
            segments = self.predictor.get_segment_analysis()
            return self._format_segment_analysis(segments)

        # ── Churn rate / statistics ──
        if any(kw in msg for kw in ["churn rate", "statistics", "summary", "how many", "total"]):
            summary = self.predictor.get_data_summary()
            return self._format_summary(summary)

        # ── Recommendations ──
        if any(kw in msg for kw in ["recommend", "strategy", "retain", "prevent", "action"]):
            return self._general_recommendations()

        # ── Default ──
        return (
            "I can help you with:\n\n"
            "1. **Customer Lookup**: Ask about any customer (e.g., 'Tell me about CUST0000001')\n"
            "2. **Risk Analysis**: 'Show top risk customers' or 'Who is most likely to churn?'\n"
            "3. **Segment Analysis**: 'Show churn by region' or 'Analyze customer segments'\n"
            "4. **Statistics**: 'What is the churn rate?' or 'Give me a data summary'\n"
            "5. **Recommendations**: 'What retention strategies do you recommend?'\n\n"
            "For best results with the Claude API, set your ANTHROPIC_API_KEY environment variable."
        )

    def _format_customer_report(self, result):
        """Format customer prediction into readable report."""
        info = result["customer_info"]
        recs = result.get("recommendations", [])

        report = f"""
**Customer Report: {result['customer_id']}**

| Metric | Value |
|--------|-------|
| Risk Level | **{result['risk_level']}** |
| Churn Probability | **{result['churn_probability']:.1%}** |
| Prediction | {result['prediction']} |
| Region | {info['region']} |
| Tenure | {info['tenure_months']} months |
| Service Type | {info['service_type']} |
| Contract Type | {info['contract_type']} |
| Avg Monthly Bill | ${info['avg_monthly_bill']:.2f} |
| Complaints | {info['complaint_count']} |
| Satisfaction Score | {info['satisfaction_score']}/5 |
| Negative Sentiment | {info['negative_sentiment_ratio']:.1%} |

**Retention Recommendations:**
"""
        for rec in recs:
            report += f"\n- [{rec['priority']}] **{rec['action']}**: {rec['detail']}"

        return report

    def _format_segment_analysis(self, segments):
        """Format segment analysis."""
        overall = segments.get("overall", {})
        report = f"""
**Customer Segment Analysis**

**Overall:**
- Total Customers: {overall.get('total_customers', 'N/A')}
- Average Churn Probability: {overall.get('avg_churn_prob', 0):.1%}
- High Risk: {overall.get('high_risk_count', 0)} | Medium: {overall.get('medium_risk_count', 0)} | Low: {overall.get('low_risk_count', 0)}

**By Region:**
"""
        for region, data in segments.get("by_region", {}).items():
            report += f"- {region}: Avg Churn={data['avg_churn_prob']:.1%}, Customers={data['customer_count']}, High Risk={data.get('high_risk_count', 0)}\n"

        report += "\n**By Contract Type:**\n"
        for ctype, data in segments.get("by_contract_type", {}).items():
            report += f"- {ctype}: Avg Churn={data['avg_churn_prob']:.1%}, Customers={data['customer_count']}\n"

        return report

    def _format_summary(self, summary):
        """Format data summary."""
        return f"""
**Data Summary:**

| Metric | Value |
|--------|-------|
| Total Customers | {summary['total_customers']:,} |
| Churn Rate | {summary['churn_rate']} |
| Avg Tenure | {summary['avg_tenure_months']} months |
| Avg Monthly Bill | ${summary['avg_monthly_bill']:.2f} |
| Avg Satisfaction | {summary['avg_satisfaction']}/5 |
| Regions | {len(summary['regions'])} |
| Service Types | {len(summary['service_types'])} |
"""

    def _general_recommendations(self):
        """Provide general retention recommendations."""
        segments = self.predictor.get_segment_analysis()
        overall = segments.get("overall", {})
        high_risk = overall.get("high_risk_count", 0)

        return f"""
**Retention Strategy Recommendations**

Based on the analysis of {overall.get('total_customers', 0):,} customers with {high_risk} high-risk accounts:

**Immediate Actions (High Risk - {high_risk} customers):**
- Launch targeted outreach program for high-risk customers
- Offer personalized retention packages (rate discounts, service upgrades)
- Assign dedicated account managers for top 20 at-risk customers

**Medium-Term Strategies:**
- Implement proactive complaint resolution workflow in SAP CRM
- Create automated satisfaction survey triggers after service interactions
- Develop early warning system integration with SAP IS-U billing alerts

**Long-Term Initiatives:**
- Build loyalty program with tenure-based rewards
- Invest in self-service portal improvements (reduce complaint volume)
- Implement predictive maintenance to reduce service outages
- Create customer health score dashboard integrated with SAP

**SAP IS-U Integration Points:**
- Configure FICA dunning to include retention offers before disconnection
- Set up automated move-out prevention workflows
- Integrate churn scores into CS agent screens (CIC0)
- Create custom SAP reports (t-code: ZCHURN) for management visibility
"""

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
