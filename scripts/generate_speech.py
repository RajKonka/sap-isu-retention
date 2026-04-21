"""
Generates the full presentation speech script as a professional PDF.
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
PATH = os.path.join(OUT, "Vantive_Presentation_Speech_Script.pdf")

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

def build():
    doc = SimpleDocTemplate(PATH, pagesize=A4,
          leftMargin=2.2*cm, rightMargin=2.2*cm,
          topMargin=2.2*cm, bottomMargin=2.2*cm)

    def S(name, **kw): return ParagraphStyle(name, **kw)

    slide_label  = S("sl", fontSize=9,  textColor=WHITE,  fontName="Helvetica-Bold",
                     alignment=TA_LEFT, leading=13)
    slide_title  = S("st", fontSize=15, textColor=NAVY,   fontName="Helvetica-Bold",
                     leading=20, spaceBefore=4, spaceAfter=2)
    speech       = S("sp", fontSize=11, textColor=BLACK,  fontName="Helvetica",
                     leading=18, spaceAfter=6, alignment=TA_JUSTIFY)
    speech_bold  = S("sb", fontSize=11, textColor=NAVY,   fontName="Helvetica-Bold",
                     leading=18, spaceAfter=4)
    note         = S("nt", fontSize=9,  textColor=GREY,   fontName="Helvetica-Oblique",
                     leading=13, spaceAfter=4, leftIndent=14)
    emphasis     = S("em", fontSize=11, textColor=BLUE,   fontName="Helvetica-Bold",
                     leading=18, spaceAfter=6, leftIndent=20)
    cue          = S("cu", fontSize=9,  textColor=WHITE,  fontName="Helvetica-Bold",
                     leading=13, alignment=TA_CENTER)
    footer_s     = S("ft", fontSize=8,  textColor=GREY,   fontName="Helvetica",
                     alignment=TA_CENTER)
    h_title      = S("ht", fontSize=26, textColor=WHITE,  fontName="Helvetica-Bold",
                     leading=32, alignment=TA_CENTER)
    h_sub        = S("hs", fontSize=13, textColor=CYAN,   fontName="Helvetica",
                     leading=18, alignment=TA_CENTER)

    def slide_band(label, color=NAVY):
        tbl = Table([[Paragraph(label, slide_label)]], colWidths=[16.6*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),color),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),10),
        ]))
        return tbl

    def cue_box(text, color=BLUE):
        tbl = Table([[Paragraph(text, cue)]], colWidths=[16.6*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),color),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("LEFTPADDING",(0,0),(-1,-1),10),
        ]))
        return tbl

    def rule():
        return HRFlowable(width="100%", thickness=1, color=CYAN, spaceAfter=6, spaceBefore=6)

    story = []

    # ── Cover ──────────────────────────────────────────────────
    cover = Table([[Paragraph(
        "PRESENTATION SPEECH SCRIPT<br/>Customer Retention Intelligence Platform",
        h_title)]], colWidths=[16.6*cm])
    cover.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY),
        ("TOPPADDING",(0,0),(-1,-1),40),("BOTTOMPADDING",(0,0),(-1,-1),40),
    ]))
    story.append(cover)
    story.append(Spacer(1,0.3*cm))

    sub = Table([[Paragraph("Raj Konka  ·  Vantive Inc.  ·  Full word-for-word script", h_sub)]], colWidths=[16.6*cm])
    sub.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),BLUE),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
    ]))
    story.append(sub)
    story.append(Spacer(1,0.5*cm))

    # How to use this script
    story.append(Paragraph("How to Use This Script", S("x", fontSize=13, textColor=NAVY,
                 fontName="Helvetica-Bold", leading=18, spaceAfter=4)))
    story.append(rule())
    for line in [
        "<b>SPEAK</b> — the main text in black is your spoken words. Read it naturally, don't rush.",
        "<b>[ Stage direction ]</b> — grey italic lines are actions: click, pause, point to screen.",
        "<b>Blue bars</b> — mark the start of each slide.",
        "<b>Timing</b> — the full presentation runs 18–22 minutes at a comfortable pace.",
        "<b>Tone</b> — calm and confident. You are not selling. You are showing them a problem they already have.",
    ]:
        story.append(Paragraph(f"  • {line}", note))
    story.append(Spacer(1,0.5*cm))

    # ── PRE-ENTRY ──────────────────────────────────────────────
    story.append(PageBreak())
    story.append(slide_band("BEFORE YOU BEGIN — Room Setup & Opening Position", GREY))
    story.append(Spacer(1,0.3*cm))
    story.append(Paragraph("Before You Walk In", slide_title))
    story.append(Paragraph(
        "Have the presentation open on the cover slide. Do not open the app yet — "
        "you will open it live during the demo section. Have a glass of water. "
        "Know the name of at least one person in the room and address them directly in the opening.", note))
    story.append(Spacer(1,0.3*cm))

    story.append(Paragraph("As You Walk In", slide_title))
    story.append(Paragraph(
        "Greet the room, shake hands, introduce yourself briefly. Then sit or stand at the front "
        "and let there be a moment of silence before you start. Don't rush into the first word.", note))
    story.append(Spacer(1,0.5*cm))

    # ── SLIDE 1: Opening ───────────────────────────────────────
    story.append(slide_band("SLIDE 1 — COVER", NAVY))
    story.append(Spacer(1,0.3*cm))
    story.append(cue_box("[ Click to show cover slide. Stand still. Make eye contact. Wait 3 seconds before speaking. ]", GREY))
    story.append(Spacer(1,0.3*cm))

    story.append(Paragraph(
        "I want to start with a number.", speech))
    story.append(Paragraph(
        "Last year, the average utility company in this market lost somewhere between 15 and 25 percent of its customers.", speech))
    story.append(Paragraph(
        "That's not a prediction. That's not a worst-case scenario. That's the industry average, right now.", speech))

    story.append(cue_box("[ Pause. Let that number land. ]", GREY))

    story.append(Paragraph(
        "The question I want to ask you today is not 'did you lose customers last year.' "
        "Almost certainly, you did.", speech))
    story.append(Paragraph(
        "The question is: did you know they were leaving before they left?", speech))

    story.append(cue_box("[ Pause again. Look around the room. ]", GREY))

    story.append(Paragraph(
        "Because if you did know — if you had a list, two weeks before each of those customers "
        "filed a cancellation, showing you exactly who was about to leave and why — "
        "what would your retention team have done differently?", speech))
    story.append(Paragraph(
        "That's what we're going to talk about today.", speech))
    story.append(Spacer(1,0.5*cm))

    # ── SLIDE 2: SITUATION ─────────────────────────────────────
    story.append(PageBreak())
    story.append(slide_band("SLIDE 2 — SITUATION: THE PROBLEM", NAVY))
    story.append(Spacer(1,0.3*cm))
    story.append(cue_box("[ Click to Situation slide. Point to the four stat boxes. ]"))
    story.append(Spacer(1,0.3*cm))

    story.append(Paragraph(
        "Here's the situation most utility companies are in right now.", speech))
    story.append(Paragraph(
        "Fifteen to twenty-five percent churn annually. "
        "Three hundred to five hundred dollars to acquire each replacement customer. "
        "And the worst part — when a customer finally calls to cancel, "
        "the research shows that seventy percent of save attempts at that point fail.", speech))
    story.append(Paragraph(
        "By the time you know they're leaving, it's already too late.", speech))

    story.append(cue_box("[ Point to the bottom stat: $0 spent on proactive retention. ]", GREY))

    story.append(Paragraph(
        "What most utilities spend on proactive retention — not reactive, proactive — is close to zero.", speech))
    story.append(Paragraph(
        "Not because they don't care. Because they can't see it coming.", speech))
    story.append(Paragraph(
        "The data is all there. It's in your complaints system. It's in your call records. "
        "It's in your satisfaction surveys. It's in the billing disputes. "
        "Your customers are telling you they're unhappy, every single week.", speech))
    story.append(Paragraph(
        "The problem is that no one is reading all of those signals together, in real time, "
        "and connecting them to a specific customer who is about to walk out the door.", speech))
    story.append(Spacer(1,0.5*cm))

    # ── SLIDE 3: TASK ──────────────────────────────────────────
    story.append(slide_band("SLIDE 3 — TASK: WHAT YOU ACTUALLY NEED", NAVY))
    story.append(Spacer(1,0.3*cm))
    story.append(cue_box("[ Click to Task slide. ]"))
    story.append(Spacer(1,0.3*cm))

    story.append(Paragraph(
        "So what does a retention team actually need?", speech))
    story.append(Paragraph(
        "Not a report that tells you your churn rate was 19% last quarter. "
        "You already know that from your finance team.", speech))
    story.append(Paragraph(
        "What you need is a list. A specific, ranked list of customers that says: "
        "these are the thirty people most likely to cancel in the next sixty days. "
        "Call them. Here's why each one is at risk. Here's what to say.", speech))

    story.append(cue_box("[ Point to the four need boxes on screen. ]", GREY))

    story.append(Paragraph(
        "You need to know who before they cancel, not after.", speech))
    story.append(Paragraph(
        "You need to understand why, not just have a number. "
        "A risk score of 84% means nothing to a call centre agent. "
        "'This customer has filed 4 complaints, called you 6 times this month, "
        "and every single comment they've written is negative' — "
        "that is something a person can act on.", speech))
    story.append(Paragraph(
        "And you need all of this without having to hire a data science team, "
        "build infrastructure, or wait six months for an enterprise implementation.", speech))
    story.append(Spacer(1,0.5*cm))

    # ── SLIDE 4: ACTION ────────────────────────────────────────
    story.append(PageBreak())
    story.append(slide_band("SLIDE 4 — ACTION: THE PLATFORM", NAVY))
    story.append(Spacer(1,0.3*cm))
    story.append(cue_box("[ Click to Action slide. Walk through the 6 steps. ]"))
    story.append(Spacer(1,0.3*cm))

    story.append(Paragraph(
        "This is what the Vantive Customer Retention Intelligence Platform does.", speech))
    story.append(Paragraph(
        "You upload your existing customer data — "
        "the files you already have, CSV or Excel, "
        "no special format required.", speech))
    story.append(Paragraph(
        "The platform automatically reads your column names and maps them to the right fields. "
        "Even if your columns are named differently from ours, it figures it out.", speech))
    story.append(Paragraph(
        "Then it does something that would take your team weeks to do manually. "
        "It reads every single complaint comment your customers have written, "
        "analyses the language, and converts it into a sentiment score. "
        "It combines that with call frequency, satisfaction ratings, billing behaviour, "
        "how long they've been with you, whether they're on autopay.", speech))
    story.append(Paragraph(
        "It builds fifty signals per customer. "
        "And it feeds all of those signals into a machine learning model "
        "that was trained specifically on utility customer churn patterns.", speech))
    story.append(Paragraph(
        "The output is a ranked list of every customer, sorted by churn probability, "
        "with a risk tier, the specific reasons they're at risk, "
        "and a recommended action.", speech))

    story.append(cue_box("[ Pause. ]", GREY))

    story.append(Paragraph(
        "From upload to results — under two minutes.", speech))
    story.append(Spacer(1,0.5*cm))

    # ── SLIDE 5: WHAT YOU GET ──────────────────────────────────
    story.append(slide_band("SLIDE 5 — WHAT YOU GET", NAVY))
    story.append(Spacer(1,0.3*cm))
    story.append(cue_box("[ Click to What You Get slide. ]"))
    story.append(Spacer(1,0.3*cm))

    story.append(Paragraph(
        "Let me be specific about what lands in your hands after you run this.", speech))
    story.append(Paragraph(
        "A ranked risk list — every customer scored zero to one hundred percent, "
        "highest risk at the top. Your team knows immediately where to start.", speech))
    story.append(Paragraph(
        "Not just a score — the reason. The platform surfaces the top three behavioural flags "
        "driving each customer's risk. So instead of calling someone and saying "
        "'our system flagged you,' your agent can say "
        "'we noticed you've had three unresolved issues and we want to make that right.'", speech))
    story.append(Paragraph(
        "A specific retention recommendation per customer. "
        "Proactive outreach call. Billing dispute resolution. Loyalty offer. Escalation to account manager. "
        "Based on what's actually driving their risk, not a generic script.", speech))
    story.append(Paragraph(
        "PDF and Excel reports, ready to download instantly. "
        "Leadership presentation ready. "
        "Agent workload ready.", speech))
    story.append(Paragraph(
        "And every single upload is saved. "
        "You log back in next month, your history is there, "
        "your previous results are there, your downloads are waiting for you.", speech))
    story.append(Spacer(1,0.5*cm))

    # ── SLIDE 6: NUROSTUDIO ────────────────────────────────────
    story.append(PageBreak())
    story.append(slide_band("SLIDE 6 — NUROSTUDIO AI ASSISTANT", NAVY))
    story.append(Spacer(1,0.3*cm))
    story.append(cue_box("[ Click to NuroStudio slide. ]"))
    story.append(Spacer(1,0.3*cm))

    story.append(Paragraph(
        "There's one more thing built into the platform that I want to spend a moment on "
        "because it addresses something I hear from retention teams constantly.", speech))
    story.append(Paragraph(
        "The problem isn't always knowing who is at risk. "
        "Sometimes the problem is knowing what to do about it.", speech))

    story.append(cue_box("[ Point to the questions on the left side of the slide. ]", GREY))

    story.append(Paragraph(
        "Built into the platform is NuroStudio — an AI assistant your team can talk to "
        "in plain English.", speech))
    story.append(Paragraph(
        "Your agent can open it and ask: "
        "'This customer has an 87 percent churn risk — what should I say when I call them?' "
        "And it answers based on that specific customer's actual data. "
        "Their complaint history. Their sentiment score. Their tenure. "
        "A recommended conversation script based on what's actually going on with them.", speech))
    story.append(Paragraph(
        "They can ask: 'We have 200 high-risk customers this week — "
        "which segment should we prioritise first?' "
        "It answers from your real data. Not a generic response.", speech))
    story.append(Paragraph(
        "And this is important — it will not make things up. "
        "If the data isn't there, it says it isn't there. "
        "If it doesn't have enough information to answer, "
        "it tells you exactly what it needs. "
        "It is not a chatbot that will confidently invent customer data "
        "and send your agent into a call with wrong information.", speech))

    story.append(cue_box("[ Pause. This point matters — let it land. ]", GREY))

    story.append(Paragraph(
        "It closes the gap between the prediction and the action. "
        "That's why we built it.", speech))
    story.append(Spacer(1,0.5*cm))

    # ── SLIDE 7: ACCURACY / MODEL ──────────────────────────────
    story.append(slide_band("SLIDE 7 — ACCURACY & HOW IT IMPROVES", NAVY))
    story.append(Spacer(1,0.3*cm))
    story.append(cue_box("[ Click to Accuracy slide. ]"))
    story.append(Spacer(1,0.3*cm))

    story.append(Paragraph(
        "I want to be straightforward with you about the model, "
        "because I think honesty here is more valuable than a sales pitch.", speech))
    story.append(Paragraph(
        "On day one, the platform uses a pre-trained model. "
        "It was built on utility industry patterns — "
        "complaint behaviour, call frequency, satisfaction trends, tenure curves. "
        "It achieves an accuracy of 80 percent and an ROC AUC of 0.83 on independent test data. "
        "For context, 0.5 is a random guess and 1.0 is perfection. "
        "0.83 is a strong, production-grade model.", speech))
    story.append(Paragraph(
        "But here's what's more powerful than that.", speech))

    story.append(cue_box("[ Point to the right panel on screen — Full Analysis mode. ]", GREY))

    story.append(Paragraph(
        "When you upload historical data that includes which of your customers actually churned — "
        "even 6 months of records — the platform retrains entirely on your customer base. "
        "It stops learning from general industry patterns "
        "and starts learning your specific customers, your specific market, "
        "your tariff structure, your geography.", speech))
    story.append(Paragraph(
        "After 6 to 12 months of real data, ROC AUC typically rises to 0.88 to 0.94. "
        "Churn reduction of 15 to 30 percent becomes achievable.", speech))
    story.append(Paragraph(
        "This is exactly the process used by the large telecoms and European utilities "
        "that run AI retention programmes. "
        "The difference is they spend millions building it. "
        "You can start today.", speech))
    story.append(Spacer(1,0.5*cm))

    # ── SLIDE 8: RESULT / ROI ──────────────────────────────────
    story.append(PageBreak())
    story.append(slide_band("SLIDE 8 — RESULT: THE BUSINESS CASE", NAVY))
    story.append(Spacer(1,0.3*cm))
    story.append(cue_box("[ Click to Result slide. Walk through the ROI example. ]"))
    story.append(Spacer(1,0.3*cm))

    story.append(Paragraph(
        "Let's talk about what this looks like in numbers.", speech))
    story.append(Paragraph(
        "Take a utility with 50,000 customers. "
        "A 20 percent churn rate means 10,000 customers lost every year. "
        "At an average annual revenue of $1,200 per customer, "
        "that's $12 million walking out the door.", speech))
    story.append(Paragraph(
        "Now — your retention team doesn't need to save all 10,000. "
        "They need to save enough to justify the cost of trying.", speech))

    story.append(cue_box("[ Point to the bottom ROI box on screen. ]", GREY))

    story.append(Paragraph(
        "If you prevent just 10 percent of that churn — 1,000 customers — "
        "at a cost of $50 per retention effort, "
        "you spend $50,000 and retain $1.2 million in revenue.", speech))
    story.append(Paragraph(
        "That is a 2,300 percent return on investment.", speech))

    story.append(cue_box("[ Pause. Do not elaborate immediately. Let them do the math themselves. ]", GREY))

    story.append(Paragraph(
        "The platform typically pays for itself within 60 to 90 days of deployment.", speech))
    story.append(Paragraph(
        "Every dollar spent on proactive retention saves five to ten dollars in acquisition cost. "
        "The earlier you identify a customer at risk, the cheaper it is to save them.", speech))
    story.append(Spacer(1,0.5*cm))

    # ── SLIDE 9: VALIDATION ────────────────────────────────────
    story.append(slide_band("SLIDE 9 — HOW YOU KNOW IT'S WORKING", NAVY))
    story.append(Spacer(1,0.3*cm))
    story.append(cue_box("[ Click to Validation slide. ]"))
    story.append(Spacer(1,0.3*cm))

    story.append(Paragraph(
        "I expect the next question in the room to be: how do we know it's accurate?", speech))
    story.append(Paragraph(
        "That's the right question, and I want to give you a direct answer.", speech))
    story.append(Paragraph(
        "First — the business sense check. "
        "After your first upload, look at the top 20 highest-risk customers the model flags. "
        "Show them to your best retention manager. "
        "Ask them: do these profiles make sense? "
        "In our experience, experienced agents immediately recognise these customers. "
        "That's the first signal.", speech))
    story.append(Paragraph(
        "Second — risk distribution. "
        "If the model flags 80 percent of your customers as high risk, something is wrong. "
        "If it flags 15 to 25 percent, that's realistic and the platform shows you this "
        "immediately after scoring.", speech))
    story.append(Paragraph(
        "Third — after 90 days, go back and check. "
        "Of the customers the model flagged as high risk, how many actually churned? "
        "That's your precision score. You can measure it yourself. "
        "No trust required — just track outcomes.", speech))
    story.append(Paragraph(
        "And fourth — every time you retrain with fresh data, "
        "the accuracy score updates. You can watch it improve. "
        "That's the proof that the model is learning your market.", speech))
    story.append(Spacer(1,0.5*cm))

    # ── SLIDE 10: WHY VANTIVE ──────────────────────────────────
    story.append(PageBreak())
    story.append(slide_band("SLIDE 10 — WHY VANTIVE", NAVY))
    story.append(Spacer(1,0.3*cm))
    story.append(cue_box("[ Click to Why Vantive slide. ]"))
    story.append(Spacer(1,0.3*cm))

    story.append(Paragraph(
        "I want to address the obvious alternative, which is building something like this internally.", speech))
    story.append(Paragraph(
        "If you have a data science team, you could build a churn model. "
        "It would take six to twelve months, cost several hundred thousand dollars in salary, "
        "and it would not include the NLP complaint analysis, "
        "the retention recommendations engine, "
        "or the AI assistant out of the box.", speech))
    story.append(Paragraph(
        "The other alternative is a large enterprise analytics platform. "
        "Those typically start at $200,000 a year and require a six-month implementation.", speech))
    story.append(Paragraph(
        "What we've built is none of those things.", speech))
    story.append(Paragraph(
        "It's purpose-built for utility customer retention. "
        "Every feature — the complaint severity analysis, the SAP IS-U data structure compatibility, "
        "the sentiment volatility flag, the autopay factor — "
        "is designed specifically for your industry, not adapted from a generic platform.", speech))
    story.append(Paragraph(
        "It works with the files you already have. "
        "No integration project. No consultant. "
        "Upload a file. Get results.", speech))
    story.append(Spacer(1,0.5*cm))

    # ── SLIDE 11: CLOSE / CTA ──────────────────────────────────
    story.append(slide_band("SLIDE 11 — CLOSE & NEXT STEPS", NAVY))
    story.append(Spacer(1,0.3*cm))
    story.append(cue_box("[ Click to final slide. Step forward slightly. ]"))
    story.append(Spacer(1,0.3*cm))

    story.append(Paragraph(
        "I'd like to show you something before we wrap up.", speech))

    story.append(cue_box("[ Open the app live — go to Upload Your Data tab. ]", colors.HexColor("#1B5E20")))

    story.append(Paragraph(
        "This is the platform running right now.", speech))
    story.append(Paragraph(
        "If you have a customer file — even a sample, even anonymised — "
        "we can run it live right here and you will see real results "
        "in under two minutes.", speech))

    story.append(cue_box("[ If they have data, run it. If not, use the sample data from sample_data/sample_set_1/. ]", colors.HexColor("#1B5E20")))

    story.append(Paragraph(
        "We offer a free trial. "
        "Upload up to 5,000 of your customers at no cost, no commitment. "
        "See your own risk list. Judge it for yourself.", speech))

    story.append(cue_box("[ Pause. ]", GREY))

    story.append(Paragraph(
        "The customers who are about to leave you — "
        "they're already in your data. "
        "They've already complained. "
        "They've already called more than twice this month. "
        "Their satisfaction scores are already low.", speech))
    story.append(Paragraph(
        "The only question is whether you read those signals before they cancel "
        "or after.", speech))

    story.append(cue_box("[ Stop. Do not add anything after this. Let there be silence. Look at the room. ]", GREY))

    story.append(Spacer(1,0.5*cm))
    story.append(rule())

    # ── Q&A PREP ───────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Q&A Preparation", S("qa", fontSize=16, textColor=NAVY,
                 fontName="Helvetica-Bold", leading=22, spaceAfter=4)))
    story.append(rule())
    story.append(Paragraph(
        "These are the questions you will almost certainly be asked. "
        "Have these answers ready.", note))
    story.append(Spacer(1,0.3*cm))

    qa = [
        (
            "Q: How accurate is it really?",
            "The base model achieves ROC AUC 0.83 and 80% accuracy on held-out test data. "
            "But the more honest answer is: after 90 days, track which high-risk customers you "
            "called and which ones churned anyway. That's your real accuracy number for your "
            "specific customer base. It's measurable. You don't have to take our word for it."
        ),
        (
            "Q: What data do we need to provide?",
            "At minimum, a customer list with a customer ID. The more you can provide — "
            "complaints, interaction records, satisfaction scores — the more accurate the predictions. "
            "We'll show you exactly which columns we need and map your format automatically."
        ),
        (
            "Q: Is our data safe?",
            "Your data never leaves your session. Every user's data is isolated in a private workspace. "
            "We never share data between organisations. And the platform can be deployed on your own "
            "infrastructure if data sovereignty is a requirement — just ask."
        ),
        (
            "Q: What if we don't have historical churn data?",
            "Start with Predict Only mode — it works from day one using the pre-trained model. "
            "As you use the platform and track which predictions were correct, "
            "you build your historical dataset naturally. After 6 months you'll have "
            "enough real data to retrain and the accuracy will jump significantly."
        ),
        (
            "Q: How is this different from our CRM?",
            "Your CRM records what happened. This platform predicts what is going to happen. "
            "A CRM tells you a customer filed 3 complaints. "
            "This platform tells you that customer has a 79% probability of leaving in the next 60 days "
            "and here's the specific action to take. Those are fundamentally different things."
        ),
        (
            "Q: What does it cost?",
            "We have a free tier for up to 5,000 customers — start there at no cost. "
            "Paid plans scale with your customer base. I'm happy to discuss pricing "
            "after you've seen it working on your own data."
        ),
        (
            "Q: How long does implementation take?",
            "There is no implementation. You register, upload a file, and get results. "
            "The longest part is preparing your data export — typically 30 minutes if you "
            "know where your files are."
        ),
        (
            "Q: What if the predictions are wrong?",
            "They will sometimes be wrong — no model is 100%. The goal is not perfection. "
            "The goal is to be right enough often enough that your retention team is calling "
            "the right customers. Even at 60% precision, you are dramatically more efficient "
            "than calling customers at random or waiting for them to complain."
        ),
    ]

    for q, a in qa:
        story.append(KeepTogether([
            Paragraph(q, S("qq", fontSize=11, textColor=NAVY, fontName="Helvetica-Bold",
                           leading=17, spaceAfter=3, spaceBefore=10)),
            Paragraph(a, S("aa", fontSize=10, textColor=BLACK, fontName="Helvetica",
                           leading=16, spaceAfter=6, leftIndent=12, alignment=TA_JUSTIFY)),
        ]))

    story.append(Spacer(1,0.8*cm))
    story.append(rule())

    # ── Timing guide ──────────────────────────────────────────
    story.append(Paragraph("Slide Timing Guide", S("tg", fontSize=13, textColor=NAVY,
                 fontName="Helvetica-Bold", leading=18, spaceAfter=4)))
    timing = [
        ["Slide", "Content", "Time"],
        ["1", "Cover + Opening", "2 min"],
        ["2", "Situation", "2 min"],
        ["3", "Task", "2 min"],
        ["4", "Action — Platform overview", "2 min"],
        ["5", "What you get", "2 min"],
        ["6", "NuroStudio", "2–3 min"],
        ["7", "Accuracy & improving", "2 min"],
        ["8", "ROI / Business case", "2 min"],
        ["9", "Validation", "1–2 min"],
        ["10", "Why Vantive", "1 min"],
        ["11", "Close + Live demo", "3–5 min"],
        ["—", "Q&A", "10–15 min"],
        ["TOTAL", "", "~20–25 min + Q&A"],
    ]
    tbl = Table(timing, colWidths=[2.0*cm, 10.6*cm, 4.0*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),
        ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),9),
        ("ROWBACKGROUNDS",(0,1),(-1,-2),[LIGHT,WHITE]),
        ("BACKGROUND",(0,-1),(-1,-1),ORANGE),
        ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
        ("TEXTCOLOR",(0,-1),(-1,-1),NAVY),
        ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#CFD8DC")),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),
    ]))
    story.append(tbl)

    story.append(Spacer(1,0.8*cm))
    story.append(rule())
    story.append(Paragraph(
        "© 2026 Vantive Inc.  ·  raj.konka@vantiveinc.com  ·  CONFIDENTIAL — DO NOT DISTRIBUTE",
        S("ft", fontSize=8, textColor=GREY, fontName="Helvetica", alignment=TA_CENTER)))

    doc.build(story)
    print(f"Speech script saved: {PATH}")

if __name__ == "__main__":
    build()
