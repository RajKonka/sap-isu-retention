"""
Generates two documents for the Vantive internal business team:
  1. Business Team Briefing Document (PDF) — detailed, plain English, no code
  2. Business Team Presentation Script (PDF) — how to walk the team through it
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "client_materials")
os.makedirs(OUT, exist_ok=True)

NAVY   = colors.HexColor("#0D2137")
BLUE   = colors.HexColor("#1565C0")
CYAN   = colors.HexColor("#00B4D8")
ORANGE = colors.HexColor("#F4A300")
GREEN  = colors.HexColor("#1B5E20")
LIGHT  = colors.HexColor("#EEF2F7")
GREY   = colors.HexColor("#546E7A")
WHITE  = colors.white
BLACK  = colors.black
RED    = colors.HexColor("#B71C1C")
YELLOW = colors.HexColor("#F9A825")

# ── Shared style helpers ──────────────────────────────────────
def S(name, **kw): return ParagraphStyle(name, **kw)

def cover_block(title, subtitle, tag, doc_width=16.6):
    els = []
    t = Table([[Paragraph(title, S("ct", fontSize=24, textColor=WHITE,
                fontName="Helvetica-Bold", leading=30, alignment=TA_CENTER))]],
              colWidths=[doc_width*cm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),NAVY),
                ("TOPPADDING",(0,0),(-1,-1),36),("BOTTOMPADDING",(0,0),(-1,-1),36)]))
    els.append(t); els.append(Spacer(1,0.25*cm))
    s = Table([[Paragraph(subtitle, S("cs", fontSize=13, textColor=WHITE,
                fontName="Helvetica", leading=18, alignment=TA_CENTER))]],
              colWidths=[doc_width*cm])
    s.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),BLUE),
                ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10)]))
    els.append(s); els.append(Spacer(1,0.25*cm))
    g = Table([[Paragraph(tag, S("cg", fontSize=9, textColor=WHITE,
                fontName="Helvetica", leading=14, alignment=TA_CENTER))]],
              colWidths=[doc_width*cm])
    g.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),NAVY),
                ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    els.append(g)
    return els

def rule(color=CYAN):
    return HRFlowable(width="100%", thickness=2, color=color, spaceAfter=8, spaceBefore=4)

def info_table(data, widths, hdr=NAVY):
    st = [("BACKGROUND",(0,0),(-1,0),hdr),("TEXTCOLOR",(0,0),(-1,0),WHITE),
          ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),
          ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#CFD8DC")),
          ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
          ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
          ("VALIGN",(0,0),(-1,-1),"TOP")]
    for i in range(1, len(data)):
        st.append(("BACKGROUND",(0,i),(-1,i),LIGHT if i%2==1 else WHITE))
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle(st))
    return t

def callout(text, bg=LIGHT, border=CYAN, label=None):
    content = f"<b>{label}</b><br/>{text}" if label else text
    t = Table([[Paragraph(content, S("co", fontSize=10, textColor=BLACK,
                fontName="Helvetica", leading=15, alignment=TA_JUSTIFY))]],
              colWidths=[16.6*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),bg),
        ("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),14),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LINEBEFORE",(0,0),(0,-1),4,border),
    ]))
    return t

def h1(text): return Paragraph(text, S("h1",fontSize=18,textColor=NAVY,
    fontName="Helvetica-Bold",leading=24,spaceBefore=20,spaceAfter=4))
def h2(text): return Paragraph(text, S("h2",fontSize=13,textColor=BLUE,
    fontName="Helvetica-Bold",leading=18,spaceBefore=12,spaceAfter=3))
def h3(text): return Paragraph(text, S("h3",fontSize=11,textColor=BLUE,
    fontName="Helvetica-Bold",leading=16,spaceBefore=8,spaceAfter=2))
def body(text): return Paragraph(text, S("b",fontSize=10,textColor=BLACK,
    fontName="Helvetica",leading=16,spaceAfter=5,alignment=TA_JUSTIFY))
def bullet(text): return Paragraph(f"• {text}", S("bl",fontSize=10,textColor=BLACK,
    fontName="Helvetica",leading=15,spaceAfter=3,leftIndent=16))
def note(text): return Paragraph(text, S("nt",fontSize=9,textColor=GREY,
    fontName="Helvetica-Oblique",leading=13,spaceAfter=4))


# ═══════════════════════════════════════════════════════════════
#  DOCUMENT 1 — BUSINESS TEAM BRIEFING
# ═══════════════════════════════════════════════════════════════

def build_business_briefing():
    path = os.path.join(OUT, "Vantive_Business_Team_Briefing.pdf")
    doc  = SimpleDocTemplate(path, pagesize=A4,
           leftMargin=2.2*cm, rightMargin=2.2*cm,
           topMargin=2.2*cm,  bottomMargin=2.2*cm)
    story = []

    for el in cover_block(
        "Business Team Briefing<br/>Customer Retention Intelligence Platform",
        "Everything your team needs to understand, use, and talk about this product",
        "Vantive Inc.  ·  Internal Use  ·  2026  ·  raj.konka@vantiveinc.com"
    ): story.append(el)
    story.append(Spacer(1,0.8*cm))

    # ── What This Document Is ──
    story.append(callout(
        "This document is written for the business team — not for developers, not for clients. "
        "It explains in plain English what our product is, what it actually does, "
        "how it works step by step, what each part means, what its limitations are, "
        "and how to talk about it confidently to a client or in a meeting.",
        bg=LIGHT, border=ORANGE, label="Purpose of this document"
    ))
    story.append(Spacer(1,0.8*cm))

    # ══ SECTION 1 ══════════════════════════════════════════════
    story.append(h1("1. What Problem Are We Solving?"))
    story.append(rule())
    story.append(body(
        "Utility companies — electricity, gas, water providers — lose customers every year. "
        "The industry term for a customer leaving is <b>churn</b>. "
        "On average, 15 to 25 percent of a utility company's customers churn every year. "
        "For a company with 50,000 customers, that is up to 12,500 people leaving annually."
    ))
    story.append(body(
        "The core problem is this: most companies only find out a customer is leaving "
        "when the customer calls to cancel. By that point, it is almost always too late to save them. "
        "Research shows that 70 percent of save attempts made after a cancellation request fail."
    ))
    story.append(body(
        "But here is the important thing: customers do not decide to leave overnight. "
        "They signal their unhappiness weeks or months in advance — through complaints, "
        "repeated support calls, low satisfaction ratings, negative feedback comments. "
        "The signals are all there in the data. Nobody is reading them in time."
    ))
    story.append(Spacer(1,0.3*cm))
    story.append(callout(
        "Our product reads all of those signals automatically, "
        "combines them using a machine learning model, "
        "and tells the retention team exactly which customers are about to leave — "
        "and why — before they cancel.",
        bg=LIGHT, border=CYAN, label="What we do"
    ))
    story.append(Spacer(1,0.5*cm))

    # ══ SECTION 2 ══════════════════════════════════════════════
    story.append(h1("2. What Data Does the Platform Use?"))
    story.append(rule())
    story.append(body(
        "The platform works with three types of customer data files that a utility company "
        "already has in their systems. The client exports these files and uploads them. "
        "No special format is required — the platform adapts to their column names automatically."
    ))

    data_types = [
        ["File Type", "What It Contains", "What We Use It For"],
        ["Customer Master",
         "One row per customer. Basic info: customer ID, name, region, how long they've been "
         "a customer, contract type, whether they're on autopay or paperless billing.",
         "Tells us who each customer is, how loyal they are (tenure), "
         "and whether they have low-friction features like autopay that reduce churn risk."],
        ["Complaints / Feedback",
         "One row per complaint. Customer ID, the text they wrote, date, severity rating, "
         "whether the issue was resolved.",
         "Tells us how unhappy they are and whether their problems are being fixed. "
         "We read the actual text they wrote to understand how negative their language is."],
        ["Service Interactions",
         "One row per interaction (call, email, chat). Customer ID, date, type, "
         "duration, whether resolved, satisfaction score they gave.",
         "Tells us how often they contact support, whether issues get resolved, "
         "and what satisfaction scores they assign after each interaction."],
    ]
    story.append(info_table(data_types, [3.0*cm, 6.5*cm, 7.1*cm]))
    story.append(note(
        "The platform works with just one file if that is all the client has. "
        "More files = more signals = better predictions."
    ))
    story.append(Spacer(1,0.5*cm))

    # ══ SECTION 3 ══════════════════════════════════════════════
    story.append(PageBreak())
    story.append(h1("3. What Happens Step by Step?"))
    story.append(rule())
    story.append(body(
        "Here is exactly what the platform does from the moment a client uploads their files "
        "to the moment they see their results. This is written in plain English — "
        "no technical knowledge required to understand it."
    ))

    steps = [
        ("Step 1", "The Client Uploads Their Files",
         "The client logs into the platform, goes to the Upload tab, and drops their CSV or Excel files. "
         "The platform reads each file and shows a preview of what it found. "
         "It automatically detects what type of data each file contains "
         "(customer records vs complaints vs interactions). "
         "If it gets it wrong, the client can correct it with a dropdown.",
         "This usually takes 30 seconds. Files up to 50MB are supported."),

        ("Step 2", "Column Matching",
         "Every company names their columns differently. "
         "One company calls it 'customer_id', another calls it 'account_number', "
         "another calls it 'cust_ref'. "
         "The platform uses fuzzy matching — a technique that finds similar-sounding words — "
         "to automatically map the client's column names to the ones our pipeline expects. "
         "The client sees the auto-matched result and can correct any mistakes before proceeding.",
         "This is why the platform works with any file format, not just ours."),

        ("Step 3", "Data Cleaning and Merging",
         "The three files are cleaned and merged into one unified record per customer. "
         "All complaint records for a customer are grouped and summarised: "
         "how many complaints did they file, what was the average severity, "
         "how many are still unresolved. "
         "All interaction records are similarly grouped: "
         "how many times did they contact support, what was their average satisfaction score, "
         "how many times per month on average.",
         "At this point, one row = one customer, with all their history combined."),

        ("Step 4", "Sentiment Analysis on Complaint Text — NLP",
         "This is one of the most important steps. "
         "For every complaint comment the customer wrote — free text like "
         "'My bill has been wrong for three months and nobody fixes it' — "
         "the platform runs a Natural Language Processing analysis called VADER. "
         "VADER reads the words and assigns a sentiment score from -1.0 (extremely negative) "
         "to +1.0 (extremely positive). "
         "It calculates per customer: the average sentiment across all their comments, "
         "what percentage of their comments were negative, "
         "and how much their sentiment swings (volatile = on the fence, one bad day could tip them).",
         "VADER is a proven NLP tool used widely in customer experience analysis. "
         "It does not need internet access and processes thousands of comments in seconds."),

        ("Step 5", "Feature Engineering — Building 50 Signals",
         "The platform now computes 50 signals per customer from all the raw data. "
         "These signals are the inputs the machine learning model will use to make its prediction. "
         "The two most important are:\n\n"
         "ENGAGEMENT SCORE — a 0 to 100 score measuring how actively the customer "
         "engages with the utility. Calculated from: how often they interact (40%), "
         "their satisfaction scores (30%), whether they have autopay (15%), "
         "and paperless billing (15%). A highly engaged customer is invested in the relationship.\n\n"
         "COMPOSITE RISK SCORE — a count from 0 to 8 of how many of the 8 risk flags "
         "are triggered for that customer. A customer with 5 or more flags is in serious danger.",
         "The 8 risk flags are: complaint risk, low satisfaction, high negative sentiment, "
         "very negative sentiment, volatile sentiment, new customer (under 12 months), "
         "frequent caller (more than 2 calls per month), unresolved issues."),

        ("Step 6", "The Machine Learning Model Scores Every Customer",
         "All 50 signals are fed into our trained machine learning model. "
         "The model was trained on patterns from 15,000 utility customers — "
         "it learned which combinations of signals predict churn. "
         "For each customer, the model outputs one number: "
         "a churn probability between 0% and 100%. "
         "This is the answer to: 'how likely is this customer to leave?'",
         "The model is an ensemble — it is actually four separate models whose predictions "
         "are averaged together. This makes it more stable and accurate than any single model."),

        ("Step 7", "Risk Tier Assignment",
         "The churn probability is converted into a risk tier:\n"
         "HIGH RISK — probability 70% or above — immediate action needed\n"
         "MEDIUM RISK — probability 40% to 69% — monitor and plan outreach\n"
         "LOW RISK — probability below 40% — healthy, routine monitoring only",
         "These tiers are what the retention team works from day to day."),

        ("Step 8", "Results, Reports, and Download",
         "The results are displayed as a sorted table — highest risk at the top. "
         "For each customer the team can see: the probability, the risk tier, "
         "the top 3 risk flags driving their score, and a recommended action. "
         "Three download options are available immediately: "
         "a PDF report for leadership, an Excel workbook for the retention team, "
         "and a CSV for any further analysis. "
         "All results are saved to the user's account history.",
         "Results persist across sessions — the client can log out and come back later "
         "and their results and downloads are still available."),
    ]

    for step_num, step_title, step_body, step_note in steps:
        story.append(KeepTogether([
            h2(f"{step_num}: {step_title}"),
            body(step_body),
            callout(step_note, bg=LIGHT, border=ORANGE),
            Spacer(1,0.3*cm),
        ]))

    # ══ SECTION 4 ══════════════════════════════════════════════
    story.append(PageBreak())
    story.append(h1("4. The Machine Learning Model — Plain English"))
    story.append(rule())
    story.append(body(
        "The phrase 'machine learning' makes people nervous. Here is what it actually means "
        "in the context of this product, with no jargon."
    ))
    story.append(h2("What is a machine learning model?"))
    story.append(body(
        "A machine learning model is a mathematical function that was trained on historical examples. "
        "We showed it 15,000 customer profiles where we already knew the outcome "
        "(this customer churned, this one stayed). "
        "It learned which combinations of signals — complaints, calls, satisfaction, tenure — "
        "appeared most often in customers who churned. "
        "Now, when it sees a new customer's signals, it applies that learned pattern "
        "to estimate how likely that person is to churn."
    ))
    story.append(callout(
        "Think of it like an experienced retention manager who has reviewed 15,000 customer cases. "
        "They've seen enough patterns to know: 'When a customer has 4 complaints, calls twice a month, "
        "and their satisfaction score dropped below 2 — they usually leave within 60 days.' "
        "The model is that experience, automated.",
        bg=LIGHT, border=CYAN
    ))
    story.append(Spacer(1,0.3*cm))

    story.append(h2("What it is NOT"))
    for item in [
        "It is not a magic answer. It is a probability estimate based on patterns. It will sometimes be wrong.",
        "It is not artificial intelligence in the way people imagine — it does not think, reason, or understand.",
        "It is not reading minds. It is finding statistical correlations between customer behaviour and churn outcomes.",
        "It is not making decisions. It is giving your retention team better information to make decisions themselves.",
    ]:
        story.append(bullet(item))
    story.append(Spacer(1,0.3*cm))

    story.append(h2("The Base Model vs Full Analysis — this is important"))
    story.append(body(
        "The platform ships with a base model — pre-trained on 15,000 synthetic (realistic but not real) "
        "utility customers. This works on day one with no client data needed. "
        "It is accurate enough to be useful immediately."
    ))
    story.append(body(
        "But the model becomes significantly more accurate when trained on the client's own historical data. "
        "When a client uploads data that includes which customers actually churned "
        "(a 'churned' column — 1 for left, 0 for stayed), "
        "the platform runs Full Analysis mode: it retrains the model entirely on their real customers. "
        "After 6 to 12 months of real data, the model becomes specific to their market and their customers."
    ))

    honest = [
        ["Question", "Honest Answer"],
        ["How accurate is the base model?",
         "ROC AUC 0.83, accuracy 80% on test data. ROC AUC measures the model's ability to "
         "separate churners from non-churners — 0.5 is random guessing, 1.0 is perfect. 0.83 is strong."],
        ["Will every prediction be right?",
         "No. Some high-risk customers will not churn. Some low-risk customers will. "
         "The goal is to be right enough often enough that the retention team is calling the right people."],
        ["What if the client has no historical churn data?",
         "Start with Predict Only mode. The base model still identifies obvious risk signals reliably. "
         "As the client uses the platform and tracks outcomes, they build their own historical dataset naturally."],
        ["Can the model be wrong in a way that causes harm?",
         "The worst case is the team calls a customer who was not going to churn, or misses one who was. "
         "Neither outcome is harmful — both are recoverable. The alternative (calling nobody proactively) is worse."],
    ]
    story.append(info_table(honest, [5.0*cm, 11.6*cm]))
    story.append(Spacer(1,0.5*cm))

    # ══ SECTION 5 ══════════════════════════════════════════════
    story.append(h1("5. NuroStudio — The AI Assistant"))
    story.append(rule())
    story.append(body(
        "Built into the platform is NuroStudio — a conversational AI assistant in the AI Assistant tab. "
        "This is different from the machine learning model. "
        "The ML model produces the numbers. NuroStudio helps your team understand and act on those numbers."
    ))
    story.append(h2("What NuroStudio actually is"))
    story.append(body(
        "NuroStudio is a large language model — the same type of AI behind tools like ChatGPT. "
        "It understands natural language questions and gives natural language answers. "
        "It is connected to the output of our ML model, "
        "so it answers questions about your actual uploaded customer data, not generic responses."
    ))
    story.append(h2("What your team can ask it"))
    questions = [
        ("'Tell me about customer CUST0000042'",
         "Returns that customer's churn probability, risk level, complaint count, "
         "sentiment score, satisfaction, and recommended actions. All real data from the model."),
        ("'Show me the top 10 highest risk customers'",
         "Returns the ranked list of highest-risk customers from the current upload."),
        ("'What is the churn risk by region?'",
         "Breaks down average churn probability across all regions in the uploaded data."),
        ("'What should I say when I call a high-risk customer with unresolved complaints?'",
         "NuroStudio gives a suggested conversation approach based on the customer's specific profile."),
        ("'Give me a summary of the dataset'",
         "Returns total customers, churn rate, risk tier breakdown, average satisfaction."),
    ]
    q_data = [["Example Question", "What it returns"]] + [[q, a] for q, a in questions]
    story.append(info_table(q_data, [6.5*cm, 10.1*cm]))
    story.append(Spacer(1,0.3*cm))

    story.append(h2("What NuroStudio will NOT do — the zero-hallucination guarantee"))
    story.append(body(
        "This is a critical point for the business team to understand and communicate to clients."
    ))
    for item in [
        "It will NEVER invent customer data, probabilities, complaint counts, or scores. If the data is not in the system, it says so.",
        "If a customer ID is asked about and that customer is not in the uploaded dataset, it says exactly that — it does not guess.",
        "If asked something outside its scope (general business questions unrelated to retention), it declines politely.",
        "If it does not have enough information to answer, it asks the user specifically what data they need to provide.",
    ]:
        story.append(bullet(item))
    story.append(callout(
        "The AI assistant was specifically engineered with strict rules to prevent hallucination. "
        "Every response is grounded in data we explicitly give it from the ML model output. "
        "It cannot access the internet, cannot make up statistics, "
        "and cannot answer customer-specific questions without their actual data present.",
        bg=LIGHT, border=GREEN, label="Important for client conversations"
    ))
    story.append(Spacer(1,0.5*cm))

    # ══ SECTION 6 ══════════════════════════════════════════════
    story.append(PageBreak())
    story.append(h1("6. What the Outputs Mean"))
    story.append(rule())
    story.append(body(
        "When a client runs a prediction, here is what they see and what each number means."
    ))

    outputs = [
        ["Output", "What It Is", "How to Interpret It"],
        ["Churn Probability",
         "A percentage from 0% to 100%",
         "87% means the model believes there is an 87% chance this customer will churn. "
         "Not a certainty — a risk estimate. Higher = more urgent."],
        ["Risk Level",
         "HIGH / MEDIUM / LOW",
         "HIGH (≥70%): Call this week. MEDIUM (40–69%): Plan outreach this month. "
         "LOW (<40%): Healthy — routine check."],
        ["Composite Risk Score",
         "A number from 0 to 8",
         "Counts how many of the 8 risk flags are triggered. "
         "5 or above = serious danger. 0–1 = healthy. Easy for agents to understand quickly."],
        ["Engagement Score",
         "A number from 0 to 100",
         "How actively the customer engages. Low score = they've mentally checked out. "
         "Below 25 combined with high churn probability = critical."],
        ["Avg Sentiment Score",
         "A number from -1.0 to +1.0",
         "-1.0 is maximally negative, +1.0 is maximally positive. "
         "Below -0.3 means even their neutral-sounding complaints carry negative undertones."],
        ["Negative Sentiment Ratio",
         "A percentage",
         "What proportion of their complaint comments were negative. "
         "Above 50% means more than half of everything they've written is negative."],
        ["Recommendation",
         "A suggested action",
         "Based on which flags fired. Not generic — tied to the specific reason for risk. "
         "'Proactive Complaint Resolution' = too many open issues. "
         "'Loyalty Offer' = high overall risk with no specific single cause."],
    ]
    story.append(info_table(outputs, [3.5*cm, 4.0*cm, 9.1*cm]))
    story.append(Spacer(1,0.5*cm))

    # ══ SECTION 7 ══════════════════════════════════════════════
    story.append(h1("7. What Are the Limitations?"))
    story.append(rule())
    story.append(body(
        "This section is important. Every product has limitations. "
        "The business team needs to know these so they are never caught off guard in a client conversation."
    ))

    limits = [
        ["Limitation", "What It Means", "What to Say to a Client"],
        ["Base model trained on synthetic data",
         "The pre-trained model learned from realistic but not real customer profiles.",
         "'The model works on day one and gives you immediate value. "
         "It becomes specific to your customers once you train it on your own historical data — "
         "typically after 6 months of uploads.'"],
        ["Predictions are probabilities, not certainties",
         "A customer flagged High Risk will not always churn. Some will stay.",
         "'No model is 100% accurate. The goal is to be right more often than random. "
         "At 80% accuracy, your team is dramatically more efficient than calling customers blindly.'"],
        ["Dashboard always shows demo data",
         "The Dashboard tab currently shows demo statistics, not the client's uploaded data.",
         "Do not demo the Dashboard with a client present. Use the Upload tab and results only."],
        ["No password reset",
         "If a registered user forgets their password, there is currently no self-service reset.",
         "Contact raj.konka@vantiveinc.com directly. We reset it manually. This is being fixed."],
        ["Free tier limit: 5,000 customers",
         "The free tier allows up to 5,000 customers per upload.",
         "'The free tier lets you score your highest-priority segment first. "
         "Paid plans handle your full customer base — we can discuss that after your trial.'"],
        ["NLP reads English complaint text best",
         "VADER was built for English. Non-English complaint text will score less accurately.",
         "Ask the client what language their complaints are in before promising NLP accuracy."],
    ]
    story.append(info_table(limits, [3.5*cm, 5.5*cm, 8.6*cm]))
    story.append(Spacer(1,0.5*cm))

    # ══ SECTION 8 ══════════════════════════════════════════════
    story.append(h1("8. How a Client Uses This Day to Day"))
    story.append(rule())
    story.append(body(
        "Here is a realistic day-to-day workflow for a retention team that has adopted the platform."
    ))

    workflow = [
        ("Weekly", "Upload the latest customer data export",
         "Export customer master, complaints, and interactions from their CRM or SAP IS-U system. "
         "Upload to the platform. Run Predict Only (or Full Analysis if they have churn history). "
         "Download the Excel report. Share the High Risk list with the retention team."),
        ("Daily", "Work the High Risk list",
         "Agents take the top 20–50 High Risk customers from the Excel workbook. "
         "For each one, they open NuroStudio and ask about that specific customer "
         "to understand the reason and get a suggested approach. Then they make the call."),
        ("Monthly", "Review outcomes and track improvement",
         "Go back to customers who were flagged High Risk last month. "
         "How many churned? How many were saved? "
         "This builds the evidence base for the ROI conversation internally."),
        ("Every 6 months", "Retrain the model on real data",
         "If the client has a churned column in their master data "
         "(showing which customers actually left), run Full Analysis. "
         "The model retrains on their real customers and accuracy improves. "
         "Compare the new ROC AUC to the previous one to show the model is improving."),
    ]
    for freq, title, desc in workflow:
        story.append(KeepTogether([
            callout(f"<b>{title}</b><br/>{desc}", bg=LIGHT, border=CYAN, label=freq),
            Spacer(1,0.2*cm),
        ]))
    story.append(Spacer(1,0.5*cm))

    # ══ SECTION 9 ══════════════════════════════════════════════
    story.append(h1("9. How to Talk About This — Key Messages"))
    story.append(rule())
    story.append(body(
        "These are the phrases and framings that work well in client conversations. "
        "Use these. Avoid the phrases in the red column."
    ))

    messaging = [
        ["Say This", "Not This"],
        ["'It reads your existing data — complaints, calls, satisfaction — and tells you who is about to leave.'",
         "'It uses AI to predict churn.' (too vague, sounds like buzzword)"],
        ["'The model achieves 80% accuracy and ROC AUC 0.83 on test data.'",
         "'It's incredibly accurate.' (unsubstantiated)"],
        ["'It tells you specifically why each customer is at risk, not just a score.'",
         "'It gives you a list of at-risk customers.' (every tool claims this)"],
        ["'It starts working on day one. It gets more accurate as your data trains it.'",
         "'You need historical data before it works.' (not true — and scary to say)"],
        ["'The AI assistant only answers from your actual data. It will not make things up.'",
         "'The AI can answer anything about your customers.' (untrue and dangerous)"],
        ["'Upload your file and see results in under 2 minutes.'",
         "'After a setup period you'll start seeing value.' (wrong — there is no setup)"],
        ["'Your data stays in your private workspace. Nothing is shared.'",
         "Avoid discussing data security unless asked — then give the full answer above."],
    ]
    t = Table(messaging, colWidths=[8.3*cm, 8.3*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),
        ("BACKGROUND",(0,1),(0,-1),colors.HexColor("#E8F5E9")),
        ("BACKGROUND",(1,1),(1,-1),colors.HexColor("#FFEBEE")),
        ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#CFD8DC")),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),8),("VALIGN",(0,0),(-1,-1),"TOP"),
    ]))
    story.append(t)

    story.append(Spacer(1,1.0*cm))
    story.append(rule(GREY))
    story.append(Paragraph(
        "INTERNAL — DO NOT DISTRIBUTE  ·  Vantive Inc.  ·  raj.konka@vantiveinc.com  ·  © 2026",
        S("ft", fontSize=8, textColor=GREY, fontName="Helvetica", alignment=TA_CENTER)
    ))

    doc.build(story)
    print(f"[1/2] Business briefing: {path}")


# ═══════════════════════════════════════════════════════════════
#  DOCUMENT 2 — BUSINESS TEAM SCRIPT
# ═══════════════════════════════════════════════════════════════

def build_business_script():
    path = os.path.join(OUT, "Vantive_Business_Team_Script.pdf")
    doc  = SimpleDocTemplate(path, pagesize=A4,
           leftMargin=2.2*cm, rightMargin=2.2*cm,
           topMargin=2.2*cm,  bottomMargin=2.2*cm)
    story = []

    for el in cover_block(
        "Business Team Walk-Through Script",
        "Word-for-word guide for explaining the platform to your team",
        "Vantive Inc.  ·  Internal Use  ·  2026  ·  raj.konka@vantiveinc.com"
    ): story.append(el)
    story.append(Spacer(1,0.6*cm))

    story.append(callout(
        "This script is for walking your own business team through the product — "
        "not a client. Your audience knows the company, they understand the business context, "
        "but they may not be technical. "
        "The goal: by the end, every person in the room understands what we built, "
        "how it works, what its limitations are, and how to talk about it confidently.",
        bg=LIGHT, border=ORANGE, label="Who this script is for"
    ))
    story.append(Spacer(1,0.4*cm))

    def section(num, title):
        t = Table([[Paragraph(f"SECTION {num} — {title.upper()}",
                   S("sl", fontSize=10, textColor=WHITE, fontName="Helvetica-Bold",
                     alignment=TA_LEFT, leading=14))]],
                  colWidths=[16.6*cm])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),NAVY),
                    ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
                    ("LEFTPADDING",(0,0),(-1,-1),10)]))
        return t

    def cue(text, color=GREY):
        t = Table([[Paragraph(text, S("cu", fontSize=9, textColor=WHITE,
                   fontName="Helvetica-Oblique", leading=13))]],
                  colWidths=[16.6*cm])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),color),
                    ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
                    ("LEFTPADDING",(0,0),(-1,-1),10)]))
        return t

    def sp(text): return Paragraph(text, S("sp", fontSize=11, textColor=BLACK,
               fontName="Helvetica", leading=18, spaceAfter=5, alignment=TA_JUSTIFY))

    def emp(text): return Paragraph(text, S("em", fontSize=11, textColor=NAVY,
               fontName="Helvetica-Bold", leading=18, spaceAfter=5))

    # ── OPENING ───────────────────────────────────────────────
    story.append(section("Opening", "Setting the Room"))
    story.append(Spacer(1,0.3*cm))
    story.append(cue("[ Have the app open on your screen — go to the Upload tab. Have sample_data/sample_set_1/ files ready to upload. ]", GREY))
    story.append(Spacer(1,0.3*cm))
    story.append(sp(
        "Before I go through everything, I want to make sure we're all on the same page "
        "about what we're building and why."
    ))
    story.append(sp(
        "This is not a theoretical product. It is running right now on my screen. "
        "By the end of this session you'll understand every piece of it — "
        "what it does, how it works, what it cannot do, and how to explain it to a client."
    ))
    story.append(sp(
        "There are no stupid questions in this session. "
        "If something is unclear, stop me. The goal is that every person in this room "
        "leaves confident enough to walk into a client meeting and explain this independently."
    ))
    story.append(Spacer(1,0.5*cm))

    # ── SECTION 1 ─────────────────────────────────────────────
    story.append(section("1", "The Problem We're Solving"))
    story.append(Spacer(1,0.3*cm))
    story.append(sp(
        "Let me start with the problem, because understanding the problem is "
        "what makes everything else make sense."
    ))
    story.append(sp(
        "Utility companies lose customers every year. The industry calls this churn. "
        "The average is 15 to 25 percent annually. "
        "For a company with 50,000 customers, that's up to 12,500 people leaving every year."
    ))
    story.append(sp(
        "Here's the thing — those customers did not decide to leave overnight. "
        "They complained multiple times. They called support more than twice a month. "
        "Their satisfaction scores dropped. They wrote negative comments. "
        "All of that data exists in the company's systems."
    ))
    story.append(emp(
        "The problem is: no one is reading all of those signals together, in real time."
    ))
    story.append(sp(
        "By the time a customer calls to cancel, it's almost always too late. "
        "Our product changes that. It reads all the signals, combines them, "
        "and tells the retention team who is about to leave — weeks before they do."
    ))
    story.append(cue("[ Pause. Check that the room is following. Ask: 'Does everyone understand the problem we're solving?' ]", GREY))
    story.append(Spacer(1,0.5*cm))

    # ── SECTION 2 ─────────────────────────────────────────────
    story.append(section("2", "What the Platform Does — The One-Sentence Version"))
    story.append(Spacer(1,0.3*cm))
    story.append(sp(
        "Here is the product in one sentence, and I want you to memorise this "
        "because it's how you explain it to anyone in under 10 seconds."
    ))
    story.append(callout(
        "\"We take a utility company's existing customer data, run it through an AI model, "
        "and give their retention team a ranked list of which customers are about to leave, "
        "why each one is at risk, and what to do about it — in under two minutes.\"",
        bg=LIGHT, border=CYAN
    ))
    story.append(Spacer(1,0.3*cm))
    story.append(sp(
        "That's it. That's the product. Everything else is detail."
    ))
    story.append(sp(
        "Now let me open the platform and walk you through exactly what happens "
        "when a client uploads their data."
    ))
    story.append(cue("[ Go to the Upload tab in the app. ]", colors.HexColor("#1B5E20")))
    story.append(Spacer(1,0.5*cm))

    # ── SECTION 3 ─────────────────────────────────────────────
    story.append(section("3", "Live Walk-Through — Upload to Results"))
    story.append(Spacer(1,0.3*cm))
    story.append(cue("[ Upload sample_data/sample_set_1/ — customer_master.csv, complaint_data.csv, interaction_data.csv ]", colors.HexColor("#1B5E20")))
    story.append(Spacer(1,0.3*cm))
    story.append(sp(
        "I'm uploading three files right now. These are sample files — "
        "realistic but not real customer data. "
        "A real client would upload exports from their SAP IS-U system or CRM."
    ))
    story.append(sp(
        "Watch what happens. The platform reads the files, "
        "detects what type of data each one contains, and shows us a preview."
    ))
    story.append(cue("[ Point to the file detection and column preview on screen. ]", GREY))
    story.append(sp(
        "This is the column matching step. Every company names their columns differently. "
        "Our platform automatically maps 'cust_id' to 'customer_id', "
        "'tenure_months' to 'account_tenure_months', and so on. "
        "The client can correct any mistakes here before running the model."
    ))
    story.append(cue("[ Click Score My Customers. ]", colors.HexColor("#1B5E20")))
    story.append(sp(
        "Now the pipeline is running. Let me tell you what's happening behind the scenes "
        "in these 60 to 90 seconds."
    ))

    pipeline_explain = [
        ("The platform merges the three files",
         "It groups all complaints per customer — how many, how severe, how many are unresolved. "
         "It groups all interaction records — how many support calls, what satisfaction scores."),
        ("It reads every complaint comment",
         "Every piece of text a customer wrote goes through sentiment analysis. "
         "A tool called VADER reads the words and scores the emotion — "
         "from -1.0 (extremely negative) to +1.0 (positive). "
         "This converts their words into a number the model can use."),
        ("It builds 50 signals per customer",
         "Including 8 binary risk flags — think of them as 8 alarm bells. "
         "If more than 4 or 5 are ringing for one customer, they are in serious trouble."),
        ("The model scores every customer",
         "All 50 signals go into the trained model. "
         "It outputs a churn probability — 0% to 100% — for every single customer."),
    ]
    for step, desc in pipeline_explain:
        story.append(KeepTogether([
            emp(f"→ {step}"),
            sp(desc),
        ]))

    story.append(cue("[ Results appear on screen. Point to the table. ]", colors.HexColor("#1B5E20")))
    story.append(sp(
        "Here are the results. Sorted by churn probability — highest risk at the top."
    ))
    story.append(sp(
        "Each customer has a probability percentage, a risk tier — High, Medium, or Low — "
        "and the specific reasons they were flagged. "
        "That last column is what makes this different. "
        "Not just a score. The reason. And a recommended action."
    ))
    story.append(sp(
        "And here are the download buttons. PDF for leadership. Excel for the retention team. CSV for analysis."
    ))
    story.append(Spacer(1,0.5*cm))

    # ── SECTION 4 ─────────────────────────────────────────────
    story.append(PageBreak())
    story.append(section("4", "The AI Assistant — NuroStudio"))
    story.append(Spacer(1,0.3*cm))
    story.append(cue("[ Go to the AI Assistant tab. ]", colors.HexColor("#1B5E20")))
    story.append(Spacer(1,0.3*cm))
    story.append(sp(
        "This is NuroStudio. This is the conversational AI layer built into the platform."
    ))
    story.append(sp(
        "The machine learning model produced the numbers. "
        "NuroStudio helps your team understand and act on those numbers."
    ))
    story.append(sp(
        "Let me show you what this means in practice."
    ))
    story.append(cue("[ Type in the chat: 'Show me the top 5 highest risk customers' ]", colors.HexColor("#1B5E20")))
    story.append(sp(
        "It returns the top 5 customers from our actual uploaded data. "
        "Not a generic response. Real data from the model we just ran."
    ))
    story.append(cue("[ Type in the chat: 'Tell me about [first customer ID from results]' ]", colors.HexColor("#1B5E20")))
    story.append(sp(
        "Now it gives us the full profile of that specific customer. "
        "Their churn probability, what's driving it, what the model recommends."
    ))
    story.append(sp(
        "Here is the most important thing I need you to understand about NuroStudio "
        "so you can explain it correctly to a client."
    ))
    story.append(emp(
        "It will not make things up."
    ))
    story.append(sp(
        "We built it with strict rules. If a customer ID is asked about that is not in the uploaded data, "
        "it says it cannot find them — it does not invent a profile. "
        "If asked something outside its scope, it declines. "
        "If asked for data that was never uploaded, it asks what data it needs."
    ))
    story.append(sp(
        "This matters because the worst thing that could happen is an agent calls a customer "
        "with incorrect information the AI invented. "
        "We engineered against that specifically."
    ))
    story.append(Spacer(1,0.5*cm))

    # ── SECTION 5 ─────────────────────────────────────────────
    story.append(section("5", "The Model — What's Actually Happening"))
    story.append(Spacer(1,0.3*cm))
    story.append(sp(
        "I want to spend a few minutes on the model itself, "
        "because people ask about it and you need to be able to answer confidently."
    ))
    story.append(sp(
        "The model is not magic. It is a mathematical function trained on patterns. "
        "We trained it on 15,000 utility customer profiles where we knew the outcome — "
        "who churned and who stayed. "
        "It learned which combinations of signals predicted churn. "
        "Now it applies that pattern to new customers."
    ))
    story.append(sp(
        "Think of it like a very experienced retention manager who has reviewed "
        "15,000 cases and knows from experience: "
        "'When a customer has called 4 times this month, filed 3 complaints, "
        "and their satisfaction dropped below 2 — they usually leave within 60 days.' "
        "That's the model. That experience, automated."
    ))
    story.append(emp("What about accuracy?"))
    story.append(sp(
        "The base model achieves 80 percent accuracy and a ROC AUC of 0.83. "
        "ROC AUC — you don't need to memorise what it stands for — "
        "just know that 0.5 means the model is guessing randomly "
        "and 1.0 means it is perfect. 0.83 is strong for a real-world prediction model."
    ))
    story.append(emp("What about the base model vs Full Analysis?"))
    story.append(sp(
        "The base model was trained on realistic but synthetic data — not a specific client's real customers. "
        "It works on day one. It gives immediate value."
    ))
    story.append(sp(
        "But when a client uploads data that includes which customers actually churned, "
        "the platform retrains on their real data. "
        "After 6 to 12 months, the model is specific to their market and their customers. "
        "That's when the accuracy jumps significantly."
    ))
    story.append(sp(
        "Be honest about this with clients. "
        "Do not oversell the base model as if it was trained on their data. "
        "Say: 'It works from day one. It gets more accurate as it learns your customers.'"
    ))
    story.append(Spacer(1,0.5*cm))

    # ── SECTION 6 ─────────────────────────────────────────────
    story.append(section("6", "Limitations — Know These Cold"))
    story.append(Spacer(1,0.3*cm))
    story.append(sp(
        "Every product has limitations. Knowing ours and being honest about them "
        "is what builds client trust. Here are the ones you need to know."
    ))
    lims = [
        ("Base model is synthetic",
         "The pre-trained model was not built on any specific client's real customers. "
         "It represents general utility patterns. This is fine for day one. "
         "It improves significantly once trained on real data."),
        ("It will sometimes be wrong",
         "Some high-risk customers will not churn. Some low-risk ones will. "
         "The goal is to be right often enough that the retention team "
         "is calling the right people more efficiently than before."),
        ("Dashboard shows demo data",
         "The Dashboard tab currently always shows our demo statistics, not the client's real upload. "
         "Do not demonstrate the Dashboard to a client. Use the Upload tab and results only. "
         "This is on our roadmap to fix."),
        ("No password reset yet",
         "If a registered user forgets their password, contact Raj directly for a manual reset. "
         "This is being built."),
        ("Free tier is 5,000 customers",
         "The free trial allows up to 5,000 customers. Larger uploads require a paid plan."),
    ]
    for title, desc in lims:
        story.append(KeepTogether([
            emp(f"⚠  {title}"),
            sp(desc),
            Spacer(1,0.1*cm),
        ]))
    story.append(Spacer(1,0.5*cm))

    # ── SECTION 7 ─────────────────────────────────────────────
    story.append(section("7", "Questions to Expect — And How to Answer Them"))
    story.append(Spacer(1,0.3*cm))
    story.append(sp(
        "These are the questions you will hear from clients or from people in your own organisation."
    ))
    qa = [
        ("Is this really AI?",
         "Yes and no — be honest. The machine learning model is powerful statistics, "
         "the same technology used by Netflix, AT&T, and every major bank for prediction. "
         "The NuroStudio assistant is genuine AI — a large language model. "
         "Together they form an AI-assisted retention system."),
        ("How do we know the predictions are right?",
         "Track your outcomes. After 90 days, go back and check how many of the High Risk customers "
         "the model flagged actually churned. That is your precision number. You measure it yourself. "
         "We also show the ROC AUC score after every training run."),
        ("What data do we need?",
         "At minimum, a customer list with a customer ID. "
         "More files — complaints, interactions — give better predictions. "
         "We show exactly what columns we need and map their format automatically."),
        ("Is our data safe?",
         "Every client's data is isolated in their own private workspace. "
         "Nothing is shared between organisations. "
         "The platform can be deployed on the client's own infrastructure on request."),
        ("What does it cost?",
         "Free trial up to 5,000 customers at no cost. "
         "Paid plans scale with customer base. Discuss pricing after the trial."),
        ("How long to set up?",
         "No setup. Register, upload a file, get results. "
         "The longest part is exporting the data from their CRM — typically 30 minutes."),
    ]
    for q, a in qa:
        story.append(KeepTogether([
            Paragraph(f"Q: {q}", S("qq", fontSize=11, textColor=NAVY,
                     fontName="Helvetica-Bold", leading=17, spaceAfter=2, spaceBefore=8)),
            Paragraph(a, S("aa", fontSize=10, textColor=BLACK,
                     fontName="Helvetica", leading=16, spaceAfter=5, leftIndent=12,
                     alignment=TA_JUSTIFY)),
        ]))
    story.append(Spacer(1,0.5*cm))

    # ── CLOSE ─────────────────────────────────────────────────
    story.append(section("Close", "Wrapping Up the Team Session"))
    story.append(Spacer(1,0.3*cm))
    story.append(sp(
        "Before I close — I want to check that everyone in this room "
        "can answer these three questions independently:"
    ))
    for q in [
        "What problem does this product solve and for who?",
        "What happens between a client uploading their file and seeing results?",
        "What are the two most important things to be honest about with a client?",
    ]:
        story.append(bullet(q))
    story.append(cue("[ Ask the room. Let people answer. Correct if needed. ]", GREY))
    story.append(Spacer(1,0.3*cm))
    story.append(sp(
        "The briefing document we prepared covers everything we talked about today in writing. "
        "Read it before any client meeting. "
        "If there is anything in it you do not understand, ask before the meeting — not during."
    ))
    story.append(sp(
        "One last thing. The best thing you can do before talking to a client "
        "is run the platform on a sample dataset yourself. "
        "Upload the sample files, look at the results, ask NuroStudio a few questions. "
        "Once you've done it yourself, you can explain it naturally — "
        "because you've actually used it."
    ))
    story.append(cue("[ End session. Keep platform open for anyone who wants to explore independently. ]", GREY))
    story.append(Spacer(1,0.8*cm))
    story.append(rule(GREY))
    story.append(Paragraph(
        "INTERNAL — DO NOT DISTRIBUTE  ·  Vantive Inc.  ·  raj.konka@vantiveinc.com  ·  © 2026",
        S("ft", fontSize=8, textColor=GREY, fontName="Helvetica", alignment=TA_CENTER)
    ))

    doc.build(story)
    print(f"[2/2] Business team script: {path}")


if __name__ == "__main__":
    build_business_briefing()
    build_business_script()
    print(f"\nDone. Files in: {OUT}")
