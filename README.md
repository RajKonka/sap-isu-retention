# ⚡ SAP IS-U Customer Retention Prediction System

An AI-powered customer retention prediction system for utility companies using SAP IS-U.
Combines ML models with Claude AI for intelligent churn prediction and retention insights.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Set your Anthropic API key for AI chatbot
export ANTHROPIC_API_KEY="your-api-key-here"

# 3. Run the application
streamlit run app.py
```

## 📁 Project Structure

```
sap-isu-retention/
├── app.py                      # Main Streamlit application
├── config.py                   # Configuration & constants
├── requirements.txt            # Python dependencies
├── data/                       # CSV data files
├── models/                     # Saved ML models
├── reports/                    # EDA plots & reports
└── src/
    ├── data_generator.py       # Synthetic SAP IS-U data generator
    ├── data_preprocessing.py   # Data cleaning, merging, encoding
    ├── eda.py                  # Exploratory Data Analysis
    ├── feature_engineering.py  # Advanced feature creation
    ├── model_training.py       # ML model training & evaluation
    ├── prediction_engine.py    # Churn prediction & risk analysis
    └── chatbot.py              # Claude AI chatbot integration
```

## 🔄 Pipeline

1. **Data Generation/Upload** — Synthetic SAP IS-U data or upload your own CSVs
2. **Preprocessing** — Clean, validate, merge all tables on customer_id
3. **EDA** — Visualizations, correlations, statistical analysis
4. **Feature Engineering** — Engagement scores, risk indicators, behavioral features
5. **Model Training** — Logistic Regression, Random Forest, Gradient Boosting, LightGBM, Ensemble
6. **Prediction Engine** — Customer-level churn predictions with risk levels
7. **AI Chatbot** — Natural language Q&A powered by Claude API

## 📊 Data Sources (SAP IS-U Mapping)

| CSV File | SAP IS-U Table | Description |
|----------|---------------|-------------|
| customer_master.csv | BUT000, FKKVKP, EVER | Business partner & contract data |
| billing_data.csv | DBERCHZ, ERCHC | Billing line items |
| consumption_data.csv | EABL, ETTIFN | Meter readings & consumption |
| interaction_data.csv | CRM_ORDERADM_H | Service interactions |
| complaint_data.csv | CRM tickets | Complaints with sentiment |
| payment_data.csv | DFKKOP | FICA payment records |
| external_demographics.csv | External sources | Census & third-party data |

## 💬 Chatbot Examples

- "Tell me about CUST0000042"
- "Show top risk customers"
- "What's the churn rate by region?"
- "What retention strategies do you recommend?"
- "Which segment has the highest churn?"

## ⚙️ Configuration

Edit `config.py` to customize:
- Number of synthetic customers (default: 5000)
- Churn rate (default: 18%)
- Model parameters
- Feature groups
- Claude model selection
