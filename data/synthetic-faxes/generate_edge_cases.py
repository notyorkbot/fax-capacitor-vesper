#!/usr/bin/env python3
"""
Generate 4 edge-case synthetic healthcare fax PDFs for Fax Capacitor testing.
These test classifier robustness against real-world problems:
  09 - Orphan cover page (no content pages followed)
  10 - Massive patient chart dump (40 pages, queue clogger)
  11 - Illegible physician handwritten notes (simulated)
  12 - Wrong provider / misdirected fax
"""

import os
import random
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import black, gray, lightgrey, white, HexColor, red
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from pypdf import PdfReader, PdfWriter

OUTPUT_DIR = "/home/claude/faxes"
os.makedirs(OUTPUT_DIR, exist_ok=True)

W, H = letter


def add_scan_artifacts(input_path, output_path, noise_level="light"):
    """Overlay gray speckles and edge shadows to simulate scanning."""
    reader = PdfReader(input_path)
    overlay_buf = io.BytesIO()
    oc = canvas.Canvas(overlay_buf, pagesize=letter)
    random.seed(99)

    if noise_level == "heavy":
        oc.setFillColor(HexColor("#00000010"))
        oc.rect(0, 0, W, H, fill=True, stroke=False)
        oc.setFillColor(HexColor("#00000016"))
        oc.rect(0, 0, 20, H, fill=True, stroke=False)
        oc.rect(W - 20, 0, 20, H, fill=True, stroke=False)
        oc.rect(0, 0, W, 15, fill=True, stroke=False)
        oc.rect(0, H - 15, W, 15, fill=True, stroke=False)
        for _ in range(80):
            x = random.uniform(10, W - 10)
            y = random.uniform(10, H - 10)
            oc.setFillColor(HexColor("#00000020"))
            oc.circle(x, y, random.uniform(0.3, 1.5), fill=True, stroke=False)
    else:
        for _ in range(20):
            x = random.uniform(20, W - 20)
            y = random.uniform(20, H - 20)
            oc.setFillColor(HexColor("#00000012"))
            oc.circle(x, y, random.uniform(0.2, 0.9), fill=True, stroke=False)

    oc.save()
    overlay_buf.seek(0)
    overlay_reader = PdfReader(overlay_buf)
    overlay_page = overlay_reader.pages[0]

    writer = PdfWriter()
    for page in reader.pages:
        page.merge_page(overlay_page)
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT 9: Orphan Cover Page — No Content Pages
# A fax cover sheet arrived but the actual document never transmitted.
# This happens when the sending machine runs out of paper, jams, or
# the connection drops after the cover page. The classifier needs to
# recognize this is a cover sheet with nothing actionable behind it.
# ═══════════════════════════════════════════════════════════════════════════

def create_orphan_cover_page():
    path = os.path.join(OUTPUT_DIR, "09_orphan_cover_page.pdf")
    c = canvas.Canvas(path, pagesize=letter)

    # Fax transmission header (auto-printed by receiving fax machine)
    c.setFont("Courier", 7)
    c.drawString(36, H - 18, "02/12/2026 08:41AM  FROM: MEADOWBROOK URGENT CARE  (555) 902-1100  TO: (555) 867-5309  P.01/03")

    # Standard fax cover sheet layout
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(W / 2, H - 70, "FAX COVER SHEET")

    c.line(50, H - 82, W - 50, H - 82)

    y = H - 110
    c.setFont("Helvetica-Bold", 11)

    # Cover sheet fields
    fields = [
        ("TO:", "Whispering Pines Family Medicine"),
        ("FAX:", "(555) 867-5309"),
        ("ATTN:", "Dr. Evelyn Sato, DO"),
        ("", ""),
        ("FROM:", "Meadowbrook Urgent Care"),
        ("FAX:", "(555) 902-1100"),
        ("PHONE:", "(555) 902-1101"),
        ("SENDER:", "Kira Johannsen, RN"),
        ("", ""),
        ("DATE:", "February 12, 2026"),
        ("PAGES:", "3 (including this cover)"),
    ]

    for label, val in fields:
        if label == "" and val == "":
            y -= 8
            continue
        c.setFont("Helvetica-Bold", 11)
        c.drawString(60, y, label)
        c.setFont("Helvetica", 11)
        c.drawString(160, y, val)
        y -= 18

    y -= 10
    c.line(50, y, W - 50, y)
    y -= 20

    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, y, "RE:")
    c.setFont("Helvetica", 11)
    c.drawString(160, y, "Patient: FERNANDEZ, LUCIA M.  (DOB 03/28/1992)")
    y -= 18
    c.drawString(160, y, "Urgent Care Visit Notes from 02/11/2026")
    y -= 18
    c.drawString(160, y, "Chief Complaint: Acute lower abdominal pain")

    y -= 30
    c.line(50, y, W - 50, y)
    y -= 20

    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, y, "COMMENTS:")
    y -= 18
    c.setFont("Helvetica", 10)
    comments = [
        "Dr. Sato — Patient presented to our urgent care last night with acute",
        "lower abdominal pain. Workup included CBC, CMP, UA, and pelvic",
        "ultrasound. Findings attached. Patient was discharged with instructions",
        "to follow up with your office within 48 hours.",
        "",
        "Please see attached visit notes and imaging report (2 pages).",
    ]
    for line in comments:
        c.drawString(70, y, line)
        y -= 14

    y -= 30

    # Urgency checkboxes
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, y, "URGENCY:")
    urgency_opts = [
        ("Routine", False),
        ("Urgent — Please review today", True),
        ("STAT — Requires immediate attention", False),
        ("For your records / FYI only", False),
    ]
    y -= 6
    for label, checked in urgency_opts:
        y -= 16
        c.rect(80, y - 1, 10, 10, fill=False)
        if checked:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(82, y + 0.5, "X")
        c.setFont("Helvetica", 10)
        c.drawString(96, y, label)

    y -= 40
    c.setFont("Helvetica", 8)
    c.drawCentredString(W / 2, y, "CONFIDENTIALITY NOTICE: This fax contains protected health information intended")
    y -= 11
    c.drawCentredString(W / 2, y, "solely for the named recipient. If received in error, notify sender at (555) 902-1100.")

    # NOTE: This is intentionally only 1 page — the cover says "3 pages"
    # but pages 2 and 3 never arrived. This tests whether the classifier
    # flags the discrepancy (cover says 3 pages, only 1 received).

    c.save()
    add_scan_artifacts(path, path, noise_level="light")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT 10: Massive Patient Chart Dump (40 pages)
# Someone faxed an entire patient chart instead of just the relevant
# order or referral. This clogs the queue and buries other faxes.
# We simulate 40 pages of varied chart content.
# ═══════════════════════════════════════════════════════════════════════════

def create_chart_dump():
    path = os.path.join(OUTPUT_DIR, "10_chart_dump_40pages.pdf")
    c = canvas.Canvas(path, pagesize=letter)

    random.seed(123)

    # ── Page 1: Cover sheet ──
    c.setFont("Courier", 7)
    c.drawString(36, H - 18, "02/07/2026 16:22PM  FROM: RIVERSIDE COMMUNITY HOSP  (555) 661-0000  TO: (555) 867-5309  P.01/40")

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W / 2, H - 60, "RIVERSIDE COMMUNITY HOSPITAL")
    c.setFont("Helvetica", 9)
    c.drawCentredString(W / 2, H - 74, "Health Information Management Department")
    c.drawCentredString(W / 2, H - 86, "1200 River Road  |  Meadowbrook, CO 80555  |  Fax: (555) 661-0001")

    c.line(50, H - 94, W - 50, H - 94)

    y = H - 120
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, y, "MEDICAL RECORDS TRANSMISSION")
    y -= 24

    c.setFont("Helvetica", 10)
    cover_info = [
        ("TO:", "Whispering Pines Family Medicine — Dr. Evelyn Sato, DO"),
        ("FAX:", "(555) 867-5309"),
        ("FROM:", "HIM Department — Riverside Community Hospital"),
        ("DATE:", "February 7, 2026"),
        ("PAGES:", "40 (including cover)"),
        ("", ""),
        ("PATIENT:", "WELLINGTON, CHARLES B."),
        ("DOB:", "11/04/1955"),
        ("MRN:", "RCH-2019-55782"),
        ("", ""),
        ("RECORDS ENCLOSED:", ""),
    ]
    for label, val in cover_info:
        if label == "" and val == "":
            y -= 8
            continue
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(190, y, val)
        y -= 16

    # List of what's in the chart
    records_list = [
        "Emergency Department Visit Notes (01/29/2026) — 4 pages",
        "Discharge Summary (02/01/2026) — 3 pages",
        "History & Physical (01/29/2026) — 3 pages",
        "Operative Report: Appendectomy (01/30/2026) — 2 pages",
        "Anesthesia Record (01/30/2026) — 2 pages",
        "Pathology Report (01/31/2026) — 1 page",
        "Laboratory Results (01/29–02/01/2026) — 6 pages",
        "Radiology Reports: CT Abdomen, Chest X-Ray (01/29/2026) — 3 pages",
        "Nursing Notes (01/29–02/01/2026) — 8 pages",
        "Medication Administration Record (01/29–02/01/2026) — 4 pages",
        "Discharge Instructions & Follow-Up Orders — 2 pages",
    ]
    c.setFont("Helvetica", 9)
    for item in records_list:
        c.drawString(80, y, f"•  {item}")
        y -= 13

    y -= 16
    c.setFont("Helvetica-Bold", 9)
    c.drawString(60, y, "NOTE: Records sent per provider request dated 02/05/2026.")
    y -= 12
    c.drawString(60, y, "Signed authorization on file (ROI #2026-0207-RCH).")

    c.showPage()

    # ── Pages 2–40: Simulated chart content ──
    # We'll create realistic-looking page headers and varied content
    # to make this genuinely 40 pages that the classifier has to process.

    sections = [
        # (section_title, page_count, content_style)
        ("EMERGENCY DEPARTMENT PHYSICIAN NOTE", 4, "narrative"),
        ("DISCHARGE SUMMARY", 3, "narrative"),
        ("HISTORY AND PHYSICAL EXAMINATION", 3, "narrative"),
        ("OPERATIVE REPORT — LAPAROSCOPIC APPENDECTOMY", 2, "narrative"),
        ("ANESTHESIA RECORD", 2, "form"),
        ("PATHOLOGY REPORT — SURGICAL SPECIMEN", 1, "lab"),
        ("LABORATORY RESULTS", 6, "lab"),
        ("RADIOLOGY REPORT", 3, "narrative"),
        ("NURSING ASSESSMENT / PROGRESS NOTES", 8, "notes"),
        ("MEDICATION ADMINISTRATION RECORD", 4, "form"),
        ("DISCHARGE INSTRUCTIONS", 2, "narrative"),
    ]

    # Narrative text blocks for different section types
    ed_narrative = [
        "CHIEF COMPLAINT: Acute abdominal pain, nausea, vomiting x 24 hours.",
        "",
        "HISTORY OF PRESENT ILLNESS:",
        "Mr. Wellington is a 70-year-old male who presents to the emergency department with",
        "a 24-hour history of progressively worsening right lower quadrant abdominal pain.",
        "Pain began periumbilically and migrated to the RLQ over approximately 8 hours.",
        "Associated symptoms include nausea with two episodes of non-bloody emesis, anorexia,",
        "and low-grade fever (Tmax 100.8F at home). Denies dysuria, hematuria, diarrhea,",
        "or melena. Last bowel movement was yesterday, normal consistency.",
        "",
        "PAST MEDICAL HISTORY:",
        "  - Hypertension (controlled, on lisinopril 20mg daily)",
        "  - Type 2 Diabetes Mellitus (on metformin 1000mg BID, last HbA1c 7.2%)",
        "  - Hyperlipidemia (on atorvastatin 40mg daily)",
        "  - Benign prostatic hyperplasia (on tamsulosin 0.4mg daily)",
        "  - Osteoarthritis, bilateral knees",
        "  - Status post right total knee arthroplasty (2019)",
        "",
        "PAST SURGICAL HISTORY: Right TKA (2019), tonsillectomy (childhood)",
        "",
        "ALLERGIES: Codeine (nausea/vomiting), Sulfa drugs (rash)",
        "",
        "MEDICATIONS (verified with pharmacy):",
        "  1. Lisinopril 20mg PO daily",
        "  2. Metformin 1000mg PO BID",
        "  3. Atorvastatin 40mg PO QHS",
        "  4. Tamsulosin 0.4mg PO daily",
        "  5. Acetaminophen 650mg PO PRN",
        "  6. Aspirin 81mg PO daily",
        "",
        "SOCIAL HISTORY: Retired electrician. Lives with wife. Former smoker (quit 2005,",
        "20 pack-year history). Occasional alcohol (1-2 beers/week). No illicit drugs.",
        "",
        "FAMILY HISTORY: Father — MI age 68. Mother — Type 2 DM, stroke age 75.",
        "Brother — colon cancer age 62 (deceased). No family history of appendicitis.",
        "",
        "REVIEW OF SYSTEMS:",
        "Constitutional: Fever, malaise, anorexia as noted. No weight loss, night sweats.",
        "HEENT: No headache, vision changes, sore throat.",
        "Cardiovascular: No chest pain, palpitations, edema.",
        "Respiratory: No cough, dyspnea, wheezing.",
        "GI: Abdominal pain and nausea as noted. No hematemesis, melena, diarrhea.",
        "GU: No dysuria, hematuria, urinary frequency.",
        "MSK: Chronic bilateral knee pain, no acute changes.",
        "Neuro: No weakness, numbness, confusion.",
    ]

    discharge_narrative = [
        "DISCHARGE SUMMARY",
        "",
        "PATIENT: Wellington, Charles B.    MRN: RCH-2019-55782    DOB: 11/04/1955",
        "ADMISSION DATE: 01/29/2026         DISCHARGE DATE: 02/01/2026",
        "ATTENDING: Dr. Anita Krishnamurthy, MD, FACS",
        "PRIMARY CARE: Dr. Evelyn Sato, DO — Whispering Pines Family Medicine",
        "",
        "PRINCIPAL DIAGNOSIS: Acute appendicitis, uncomplicated (K35.80)",
        "",
        "SECONDARY DIAGNOSES:",
        "  - Type 2 Diabetes Mellitus (E11.65)",
        "  - Essential Hypertension (I10)",
        "  - Hyperlipidemia (E78.5)",
        "",
        "PROCEDURES: Laparoscopic appendectomy (01/30/2026)",
        "",
        "HOSPITAL COURSE:",
        "Patient admitted from ED with clinical and CT findings consistent with acute",
        "appendicitis. Surgical consult obtained. Patient taken to OR on hospital day 2",
        "for laparoscopic appendectomy, which was performed without complication.",
        "Pathology confirmed acute suppurative appendicitis without perforation.",
        "",
        "Postoperative course was uncomplicated. Patient tolerated clear liquids on POD0,",
        "advanced to regular diet by POD1. Pain well controlled with acetaminophen and",
        "low-dose oxycodone. Diabetes managed with sliding scale insulin inpatient;",
        "home metformin resumed on POD1 with meals. Blood glucose ranged 130-188 mg/dL.",
        "",
        "DISCHARGE CONDITION: Stable, afebrile, tolerating PO, ambulating independently.",
        "",
        "DISCHARGE MEDICATIONS:",
        "  1. Resume all home medications (lisinopril, metformin, atorvastatin, tamsulosin)",
        "  2. Acetaminophen 650mg PO Q6H PRN pain (first-line)",
        "  3. Oxycodone 5mg PO Q6H PRN severe pain (#10, no refills)",
        "  4. Docusate 100mg PO BID while taking oxycodone",
        "",
        "FOLLOW-UP:",
        "  - Dr. Krishnamurthy (Surgery): 2 weeks post-op, call (555) 661-0050",
        "  - Dr. Sato (PCP): 1 week for diabetes/BP check, call (555) 867-5309",
        "  - Return to ED for: fever >101.5, worsening pain, wound redness/drainage,",
        "    inability to tolerate fluids, persistent vomiting",
    ]

    hp_narrative = [
        "HISTORY AND PHYSICAL EXAMINATION",
        "",
        "PATIENT: Wellington, Charles B.    MRN: RCH-2019-55782",
        "DATE: 01/29/2026    TIME: 19:45",
        "EXAMINER: Dr. Anita Krishnamurthy, MD, FACS (Surgical Consult)",
        "",
        "PHYSICAL EXAMINATION:",
        "",
        "VITALS: T 101.2F, HR 92, BP 148/82, RR 18, SpO2 97% RA",
        "GENERAL: Alert, oriented, in moderate distress, lying still.",
        "HEENT: Atraumatic, normocephalic. Mucous membranes dry. No JVD.",
        "CARDIOVASCULAR: Regular rate and rhythm. No murmurs, gallops, or rubs.",
        "LUNGS: Clear to auscultation bilaterally. No wheezes or crackles.",
        "ABDOMEN: Soft, non-distended. Marked tenderness at McBurney's point.",
        "  Positive rebound tenderness RLQ. Positive Rovsing's sign.",
        "  No guarding in other quadrants. Bowel sounds hypoactive.",
        "  No hepatosplenomegaly. No pulsatile masses.",
        "RECTAL: Deferred per patient preference (CT obtained).",
        "EXTREMITIES: No edema. 2+ DP pulses bilaterally. Well-healed RKR scar.",
        "SKIN: Warm, dry. No rashes or lesions.",
        "NEURO: A&Ox3. CN II-XII grossly intact. Gait deferred due to pain.",
        "",
        "ASSESSMENT AND PLAN:",
        "70-year-old male with clinical presentation consistent with acute appendicitis.",
        "CT abdomen/pelvis demonstrates enlarged appendix (12mm) with periappendiceal",
        "fat stranding and small appendicolith, without evidence of perforation or abscess.",
        "",
        "Plan: Laparoscopic appendectomy in the morning. NPO after midnight.",
        "IV antibiotics (cefoxitin) initiated. Hold metformin perioperatively.",
        "Diabetes management per medicine consult. Type and screen obtained.",
        "Informed consent obtained — patient understands risks including conversion",
        "to open procedure, bleeding, infection, and anesthesia risks.",
    ]

    or_narrative = [
        "OPERATIVE REPORT",
        "",
        "PATIENT: Wellington, Charles B.    MRN: RCH-2019-55782",
        "DATE OF SURGERY: 01/30/2026",
        "SURGEON: Dr. Anita Krishnamurthy, MD, FACS",
        "ASSISTANT: Dr. Ryan Kimball, DO (PGY-4 Surgery Resident)",
        "ANESTHESIA: General endotracheal (Dr. Patricia Hwang, MD)",
        "",
        "PREOPERATIVE DIAGNOSIS: Acute appendicitis",
        "POSTOPERATIVE DIAGNOSIS: Acute suppurative appendicitis, non-perforated",
        "",
        "PROCEDURE: Laparoscopic appendectomy",
        "",
        "FINDINGS: Appendix was acutely inflamed, erythematous, and edematous",
        "measuring approximately 10cm. No perforation identified. Small amount of",
        "turbid periappendiceal fluid aspirated and sent for culture. Cecum and",
        "terminal ileum appeared normal. No other intra-abdominal pathology noted.",
        "",
        "ESTIMATED BLOOD LOSS: <10 mL",
        "SPECIMENS: Appendix to pathology",
        "DRAINS: None",
        "COMPLICATIONS: None",
        "",
        "DESCRIPTION OF PROCEDURE:",
        "Patient placed supine, general anesthesia induced without difficulty.",
        "Abdomen prepped and draped in sterile fashion. Peritoneal access obtained",
        "at umbilicus using Veress needle technique. 12mm trocar placed. Pneumo-",
        "peritoneum established to 15mmHg. Two additional 5mm trocars placed under",
        "direct visualization in the suprapubic and left lower quadrant positions.",
        "",
        "Appendix identified and found to be acutely inflamed as described above.",
        "Mesoappendix divided using LigaSure device. Appendiceal base secured with",
        "two endoscopic loops and divided. Specimen placed in retrieval bag and",
        "removed through the umbilical port. Periappendiceal fluid irrigated and",
        "aspirated. Hemostasis confirmed. Trocars removed under direct visualization.",
        "Fascia at umbilical site closed with 0-Vicryl. Skin closed with 4-0 Monocryl",
        "subcuticular suture. Steri-strips and sterile dressings applied.",
        "",
        "Patient extubated in OR, transferred to PACU in stable condition.",
    ]

    pathology_narrative = [
        "SURGICAL PATHOLOGY REPORT",
        "",
        "PATIENT: Wellington, Charles B.    MRN: RCH-2019-55782",
        "COLLECTED: 01/30/2026    REPORTED: 01/31/2026",
        "PATHOLOGIST: Dr. Samuel Osei-Mensah, MD",
        "",
        "SPECIMEN: Appendix (laparoscopic appendectomy)",
        "",
        "GROSS DESCRIPTION:",
        "Received fresh, labeled 'appendix,' is a vermiform appendix measuring",
        "9.5 x 1.8 cm. The serosal surface is erythematous and dull with fibrinous",
        "exudate. The wall thickness is up to 0.5 cm. The lumen contains purulent",
        "material. An appendicolith measuring 0.4 cm is identified at the mid-portion.",
        "Representative sections submitted in cassettes A1-A3.",
        "",
        "MICROSCOPIC DESCRIPTION:",
        "Sections demonstrate transmural acute inflammation with extensive neutrophilic",
        "infiltration of the muscularis propria and serosa. Mucosal ulceration is present.",
        "Fibrinopurulent exudate is noted on the serosal surface. No perforation,",
        "granulomatous inflammation, or neoplasia identified.",
        "",
        "DIAGNOSIS: APPENDIX, APPENDECTOMY — ACUTE SUPPURATIVE APPENDICITIS",
        "  - No perforation",
        "  - No dysplasia or malignancy",
        "  - Appendicolith present",
    ]

    # Lab results pages content
    lab_headers = [
        ("COMPREHENSIVE METABOLIC PANEL", "01/29/2026 19:30"),
        ("COMPLETE BLOOD COUNT WITH DIFF", "01/29/2026 19:30"),
        ("URINALYSIS", "01/29/2026 20:15"),
        ("BASIC METABOLIC PANEL — POD 0", "01/30/2026 16:00"),
        ("CBC — POD 1", "01/31/2026 06:00"),
        ("BMP — DISCHARGE", "02/01/2026 06:00"),
    ]

    cmp_results = [
        ("Glucose", "188", "H", "mg/dL", "70-100"),
        ("BUN", "22", "", "mg/dL", "7-20"),
        ("Creatinine", "1.1", "", "mg/dL", "0.7-1.3"),
        ("Sodium", "139", "", "mEq/L", "136-145"),
        ("Potassium", "4.2", "", "mEq/L", "3.5-5.1"),
        ("Chloride", "101", "", "mEq/L", "98-106"),
        ("CO2", "24", "", "mEq/L", "21-32"),
        ("Calcium", "9.1", "", "mg/dL", "8.5-10.5"),
        ("Total Protein", "7.0", "", "g/dL", "6.0-8.3"),
        ("Albumin", "3.8", "", "g/dL", "3.5-5.5"),
        ("Bilirubin, Total", "0.9", "", "mg/dL", "0.1-1.2"),
        ("Alk Phosphatase", "78", "", "U/L", "44-147"),
        ("AST", "28", "", "U/L", "10-40"),
        ("ALT", "32", "", "U/L", "7-56"),
    ]

    cbc_results = [
        ("WBC", "14.8", "H", "x10^3/uL", "4.5-11.0"),
        ("RBC", "4.85", "", "x10^6/uL", "4.30-5.90"),
        ("Hemoglobin", "14.5", "", "g/dL", "13.0-17.5"),
        ("Hematocrit", "43.2", "", "%", "38.3-48.6"),
        ("Platelet Count", "268", "", "x10^3/uL", "150-400"),
        ("Neutrophils", "82.4", "H", "%", "40-70"),
        ("Lymphocytes", "10.2", "L", "%", "20-45"),
        ("Monocytes", "5.8", "", "%", "2-10"),
        ("Bands", "6", "H", "%", "0-5"),
    ]

    nursing_note_templates = [
        "Admission assessment completed. Patient alert, oriented x3. Denies chest pain or "
        "shortness of breath. Abdominal pain rated 7/10, RLQ. IV access established, "
        "20g in L forearm. Labs drawn and sent. Foley not indicated at this time. "
        "Fall risk: moderate (Morse score 45). Skin intact, no pressure injuries noted. "
        "Allergies banded. ID verified x2.",

        "0200 — Resting comfortably. VS stable: T 100.4, HR 84, BP 138/78. Pain 5/10 "
        "after morphine 4mg IV given at 0130. Abdomen soft, tender RLQ. No emesis since "
        "admission. NPO maintained. IV LR running at 125 mL/hr. Awaiting OR scheduling.",

        "Pre-op checklist completed. Consent signed and in chart. H&P present and current. "
        "Labs reviewed — no critical values. Type and screen on file. NPO since midnight "
        "confirmed. Metformin held per anesthesia. Home medications held this AM. "
        "Pre-op antibiotics (cefoxitin 2g IV) administered at 0715. Patient and wife "
        "updated on plan, verbalized understanding. OR transport called.",

        "Post-op recovery note: Patient returned from OR at 1045, alert, MAE x4. "
        "Vitals: T 98.9, HR 78, BP 132/76, SpO2 98% 2L NC. Incision sites CDI, "
        "dressings dry and intact x3. Pain 4/10, managed with acetaminophen 1g IV. "
        "Anti-emetic given prophylactically. Clear liquids offered, tolerated well. "
        "Ambulated to bedside commode with assistance x1 at 1400.",

        "Day shift assessment — POD 1. Patient in good spirits, ambulating in hallway "
        "independently. Tolerating regular diet without nausea. BG this AM: 156 mg/dL. "
        "Resumed home metformin with breakfast. Pain 2/10, managed with PO acetaminophen "
        "only — declined oxycodone. Incisions clean, no erythema or drainage. "
        "Afebrile x 18 hours. D/C planning initiated with case management.",

        "Discharge nursing note: All discharge criteria met. Final vitals: T 98.6, "
        "HR 72, BP 128/74. Patient ambulating independently, tolerating regular diet, "
        "pain controlled on PO meds only. Discharge medications reviewed with patient "
        "and wife. Written instructions provided. Follow-up appointments confirmed. "
        "Patient verbalized understanding of wound care, activity restrictions, and "
        "return precautions. Discharged home with wife at 1430. Wheelchair to car.",
    ]

    mar_entries = [
        ("01/29 20:00", "Morphine 4mg IV", "Pain 7/10", "Given per order"),
        ("01/29 22:00", "Cefoxitin 2g IV", "Pre-op prophylaxis", "Infused over 30 min"),
        ("01/29 22:00", "Ondansetron 4mg IV", "Nausea", "Given per PRN order"),
        ("01/30 06:00", "Insulin lispro 4 units SQ", "BG 210", "Per sliding scale"),
        ("01/30 07:15", "Cefoxitin 2g IV", "Pre-op dose", "Infused over 30 min"),
        ("01/30 11:30", "Acetaminophen 1g IV", "Post-op pain", "Given in PACU"),
        ("01/30 16:00", "Metformin 1000mg PO", "Home med resumed", "With dinner"),
        ("01/30 22:00", "Acetaminophen 650mg PO", "Pain 3/10", "Given per order"),
        ("01/31 06:00", "Lisinopril 20mg PO", "Home med", "Given with water"),
        ("01/31 06:00", "Metformin 1000mg PO", "Home med", "With breakfast"),
        ("01/31 06:00", "Atorvastatin 40mg PO", "Home med", "Given"),
        ("01/31 08:00", "Acetaminophen 650mg PO", "Pain 2/10", "Given per order"),
        ("02/01 06:00", "All home meds given", "See MAR detail", "Discharge day"),
    ]

    radiology_narrative = [
        "RADIOLOGY REPORT",
        "",
        "CT ABDOMEN AND PELVIS WITH IV CONTRAST",
        "",
        "PATIENT: Wellington, Charles B.    MRN: RCH-2019-55782",
        "DATE: 01/29/2026    TIME: 20:30",
        "ORDERING PROVIDER: Dr. R. Vasquez, MD (Emergency Medicine)",
        "RADIOLOGIST: Dr. Janet Cho, MD",
        "",
        "CLINICAL INDICATION: RLQ pain, fever, elevated WBC. R/O appendicitis.",
        "",
        "TECHNIQUE: Helical CT of the abdomen and pelvis with IV contrast (Omnipaque",
        "350, 100 mL) acquired in portal venous phase. Coronal and sagittal reformats.",
        "",
        "COMPARISON: None available in our system.",
        "",
        "FINDINGS:",
        "",
        "APPENDIX: The appendix is dilated, measuring 12 mm in maximal diameter",
        "(normal <6mm). An appendicolith measuring 4mm is identified at the",
        "mid-portion. There is periappendiceal fat stranding and mild free fluid",
        "in the pelvis. No evidence of perforation or discrete abscess formation.",
        "",
        "LIVER: Normal size and attenuation. No focal lesions.",
        "GALLBLADDER: Normal. No stones or wall thickening.",
        "PANCREAS: Normal. No ductal dilatation.",
        "SPLEEN: Normal size.",
        "KIDNEYS: Bilateral simple cortical cysts (right 1.2cm, left 0.8cm).",
        "No hydronephrosis or stones. Normal enhancement.",
        "ADRENALS: Normal bilaterally.",
        "AORTA: Mild atherosclerotic calcification. No aneurysm.",
        "BOWEL: No obstruction or wall thickening (other than appendix).",
        "BLADDER: Normal. Foley catheter not present.",
        "LYMPH NODES: No pathologic lymphadenopathy.",
        "BONES: Degenerative changes lumbar spine. Right TKA hardware in place.",
        "",
        "IMPRESSION:",
        "1. Acute appendicitis with appendicolith. No perforation or abscess.",
        "2. Incidental bilateral simple renal cysts — benign, no follow-up needed.",
        "3. Mild aortic atherosclerosis.",
    ]

    discharge_instructions = [
        "DISCHARGE INSTRUCTIONS",
        "",
        "PATIENT: Wellington, Charles B.    DATE: 02/01/2026",
        "",
        "You had surgery to remove your appendix (laparoscopic appendectomy).",
        "Your surgery went well and you are ready to go home.",
        "",
        "WOUND CARE:",
        "- You have 3 small incisions on your abdomen covered with Steri-strips",
        "- Keep incisions clean and dry for 48 hours, then you may shower",
        "- Do not submerge incisions in bath/pool/hot tub for 2 weeks",
        "- Steri-strips will fall off on their own in 7-10 days",
        "- If incisions become red, swollen, warm, or drain pus, call your surgeon",
        "",
        "ACTIVITY:",
        "- No heavy lifting (>10 lbs) for 2 weeks",
        "- Walk daily — start with short walks and increase gradually",
        "- You may climb stairs carefully",
        "- No driving while taking oxycodone",
        "- You may return to light activity in 1-2 weeks",
        "- Full activity typically resumes in 3-4 weeks",
        "",
        "DIET:",
        "- Resume your regular diet",
        "- Drink plenty of fluids",
        "- Eat high-fiber foods to prevent constipation",
        "",
        "MEDICATIONS:",
        "- Resume all your home medications (lisinopril, metformin, atorvastatin, tamsulosin)",
        "- Take acetaminophen (Tylenol) 650mg every 6 hours as needed for pain",
        "- Take oxycodone 5mg every 6 hours ONLY for severe pain not helped by Tylenol",
        "- Take docusate (Colace) 100mg twice daily while taking oxycodone",
        "- CHECK YOUR BLOOD SUGAR more often for the next few days — surgery and",
        "  stress can affect your levels",
        "",
        "FOLLOW-UP APPOINTMENTS:",
        "- SURGEON: Dr. Krishnamurthy — 2 weeks — call (555) 661-0050 to schedule",
        "- PRIMARY CARE: Dr. Sato — 1 week for diabetes/BP check — call (555) 867-5309",
        "",
        "RETURN TO EMERGENCY DEPARTMENT IF YOU HAVE:",
        "- Fever over 101.5 degrees F",
        "- Severe or worsening abdominal pain",
        "- Redness, swelling, or pus draining from incisions",
        "- Unable to keep down fluids for more than 24 hours",
        "- Persistent vomiting",
        "- No bowel movement for more than 3 days",
    ]

    page_num = 2

    def draw_page_header(c, section_title, page_num, total=40):
        """Standard header for each chart page."""
        c.setFont("Courier", 7)
        c.drawString(36, H - 18,
            f"02/07/2026 16:22PM  FROM: RIVERSIDE COMMUNITY HOSP  (555) 661-0000  "
            f"TO: (555) 867-5309  P.{page_num:02d}/{total}")
        c.setFont("Helvetica", 7)
        c.drawString(36, H - 32, "Wellington, Charles B.  |  DOB: 11/04/1955  |  MRN: RCH-2019-55782")
        c.drawRightString(W - 36, H - 32, section_title)
        c.line(36, H - 38, W - 36, H - 38)
        return H - 54

    def write_text_lines(c, y, lines, font="Helvetica", size=9, indent=50):
        """Write lines of text, handling page breaks."""
        for line in lines:
            if y < 60:
                return y, True  # need new page
            if line == "":
                y -= 8
                continue
            if line.startswith("  ") or line.startswith("- "):
                c.setFont(font, size)
                c.drawString(indent + 15, y, line.strip())
            elif line.endswith(":") or line.isupper() or line.startswith("PATIENT:") or line.startswith("DATE"):
                c.setFont("Helvetica-Bold", size)
                c.drawString(indent, y, line)
                c.setFont(font, size)
            else:
                c.setFont(font, size)
                c.drawString(indent, y, line)
            y -= 12
        return y, False

    def write_lab_table(c, y, title, date_time, results):
        c.setFont("Helvetica-Bold", 9)
        c.drawString(50, y, f"{title}  —  Collected: {date_time}")
        y -= 14
        c.setFont("Helvetica-Bold", 7)
        cols = [50, 180, 260, 300, 350, 430]
        for col, hdr in zip(cols, ["TEST", "RESULT", "FLAG", "UNITS", "REF RANGE", "STATUS"]):
            c.drawString(col, y, hdr)
        y -= 4
        c.line(50, y, W - 50, y)
        y -= 11
        c.setFont("Helvetica", 7)
        for test, result, flag, units, ref in results:
            if y < 60:
                break
            c.drawString(50, y, test)
            if flag:
                c.setFillColor(red)
                c.setFont("Helvetica-Bold", 7)
            c.drawString(180, y, result)
            c.drawString(260, y, flag)
            c.setFillColor(black)
            c.setFont("Helvetica", 7)
            c.drawString(300, y, units)
            c.drawString(350, y, ref)
            c.drawString(430, y, "Final")
            y -= 10
        y -= 8
        return y

    # ── ED Notes (4 pages) ──
    for p in range(4):
        y = draw_page_header(c, "EMERGENCY DEPARTMENT NOTE", page_num)
        start = p * 12
        chunk = ed_narrative[start:start + 12] if start < len(ed_narrative) else [
            f"(ED Note continued — clinical documentation page {p+1})",
            "",
            "EMERGENCY DEPARTMENT COURSE:",
            "IV access established. Labs drawn and sent. CT abdomen/pelvis ordered.",
            "Morphine 4mg IV given for pain with good effect. NPO initiated.",
            "CT resulted — findings consistent with acute appendicitis (see radiology report).",
            "Surgical consult called — Dr. Krishnamurthy evaluated patient at bedside.",
            "Decision made for laparoscopic appendectomy in the morning.",
            "Patient admitted to surgical service. Pre-op orders entered.",
            "",
            "DISPOSITION: Admitted to Surgery — Dr. Krishnamurthy",
            "CONDITION AT DISPOSITION: Stable, pain controlled",
        ]
        y, _ = write_text_lines(c, y, chunk)
        if p == 3:
            y -= 10
            c.setFont("Helvetica-Bold", 8)
            c.drawString(50, y, "Electronically signed by: Dr. Ricardo Vasquez, MD — Emergency Medicine")
            c.setFont("Helvetica", 7)
            y -= 10
            c.drawString(50, y, "Signed: 01/30/2026 02:15  |  Attending Attestation Complete")
        c.showPage()
        page_num += 1

    # ── Discharge Summary (3 pages) ──
    chunk_size = len(discharge_narrative) // 3 + 1
    for p in range(3):
        y = draw_page_header(c, "DISCHARGE SUMMARY", page_num)
        start = p * chunk_size
        chunk = discharge_narrative[start:start + chunk_size]
        if p == 2 and not chunk:
            chunk = [
                "PENDING RESULTS AT DISCHARGE:",
                "  - Appendiceal fluid culture — pending (will call patient with results)",
                "",
                "ATTENDING ATTESTATION:",
                "I have personally seen and examined the patient. I reviewed the resident's",
                "note and agree with the documented history, exam, assessment and plan.",
                "",
                "Electronically signed by: Dr. Anita Krishnamurthy, MD, FACS",
                "Date signed: 02/01/2026 15:30",
            ]
        y, _ = write_text_lines(c, y, chunk)
        c.showPage()
        page_num += 1

    # ── H&P (3 pages) ──
    chunk_size = len(hp_narrative) // 3 + 1
    for p in range(3):
        y = draw_page_header(c, "HISTORY AND PHYSICAL", page_num)
        start = p * chunk_size
        chunk = hp_narrative[start:start + chunk_size]
        if not chunk:
            chunk = ["(H&P continued — see prior page)"]
        y, _ = write_text_lines(c, y, chunk)
        c.showPage()
        page_num += 1

    # ── Operative Report (2 pages) ──
    chunk_size = len(or_narrative) // 2 + 1
    for p in range(2):
        y = draw_page_header(c, "OPERATIVE REPORT", page_num)
        start = p * chunk_size
        chunk = or_narrative[start:start + chunk_size]
        y, _ = write_text_lines(c, y, chunk)
        c.showPage()
        page_num += 1

    # ── Anesthesia Record (2 pages — form style) ──
    for p in range(2):
        y = draw_page_header(c, "ANESTHESIA RECORD", page_num)
        if p == 0:
            anes_info = [
                "ANESTHESIA RECORD — PAGE 1",
                "",
                "PATIENT: Wellington, Charles B.    ASA CLASS: III",
                "PROCEDURE: Laparoscopic Appendectomy",
                "ANESTHESIOLOGIST: Dr. Patricia Hwang, MD",
                "CRNA: Michael Torres, CRNA",
                "DATE: 01/30/2026    OR START: 0830    OR END: 0945",
                "",
                "ANESTHESIA TYPE: General Endotracheal",
                "AIRWAY: Macintosh 3, Grade I view, ETT 7.5 oral, secured at 22cm",
                "INDUCTION: Propofol 200mg, Fentanyl 100mcg, Rocuronium 40mg",
                "MAINTENANCE: Sevoflurane 1.5-2.0% in O2/Air (50:50)",
                "REVERSAL: Sugammadex 200mg",
                "TOTAL FLUIDS: LR 1200 mL",
                "EBL: <10 mL",
                "UOP: Not catheterized (short case)",
                "",
                "MONITORING: Standard ASA monitors, ETCO2, temp, NMT",
                "",
                "INTRAOP VITALS (Q5 min):",
                "  0830  HR 82  BP 142/84  SpO2 99%  ETCO2 36",
                "  0835  HR 78  BP 128/76  SpO2 100% ETCO2 34",
                "  0840  HR 75  BP 122/72  SpO2 100% ETCO2 35",
                "  0845  HR 80  BP 118/70  SpO2 100% ETCO2 34  (insufflation)",
                "  0850  HR 84  BP 132/78  SpO2 99%  ETCO2 38",
                "  0900  HR 76  BP 124/74  SpO2 100% ETCO2 36",
                "  0915  HR 72  BP 120/70  SpO2 100% ETCO2 34",
                "  0930  HR 70  BP 118/68  SpO2 100% ETCO2 33  (desufflation)",
                "  0940  HR 74  BP 126/76  SpO2 100% ETCO2 35  (emergence)",
                "  0945  HR 80  BP 138/82  SpO2 98%  (extubated, to PACU)",
            ]
        else:
            anes_info = [
                "ANESTHESIA RECORD — PAGE 2",
                "",
                "PRE-ANESTHESIA EVALUATION:",
                "Reviewed H&P, labs, medications, allergies. Patient examined.",
                "NPO >8 hours confirmed. Airway: Mallampati II, good mouth opening,",
                "adequate neck mobility. No predictors of difficult intubation.",
                "",
                "Discussed risks of general anesthesia including but not limited to:",
                "sore throat, dental injury, nausea, aspiration, allergic reaction,",
                "awareness, nerve injury, and rarely death.",
                "",
                "Patient consents to anesthesia. Questions answered.",
                "",
                "POST-ANESTHESIA NOTE (PACU):",
                "Patient extubated in OR without difficulty. Transported to PACU.",
                "Alert, following commands. Vitals stable. Pain managed. Aldrete 9/10.",
                "",
                "Electronically signed: Dr. Patricia Hwang, MD — Anesthesiology",
            ]
        y, _ = write_text_lines(c, y, anes_info)
        c.showPage()
        page_num += 1

    # ── Pathology (1 page) ──
    y = draw_page_header(c, "PATHOLOGY REPORT", page_num)
    y, _ = write_text_lines(c, y, pathology_narrative)
    y -= 14
    c.setFont("Helvetica-Bold", 8)
    c.drawString(50, y, "Electronically signed: Dr. Samuel Osei-Mensah, MD — Anatomic Pathology")
    c.showPage()
    page_num += 1

    # ── Lab Results (6 pages) ──
    for p in range(6):
        y = draw_page_header(c, "LABORATORY RESULTS", page_num)
        if p == 0:
            y = write_lab_table(c, y, "COMPREHENSIVE METABOLIC PANEL", "01/29/2026 19:30", cmp_results)
        elif p == 1:
            y = write_lab_table(c, y, "COMPLETE BLOOD COUNT WITH DIFF", "01/29/2026 19:30", cbc_results)
        elif p == 2:
            ua_results = [
                ("Color", "Yellow", "", "", "Yellow"),
                ("Clarity", "Hazy", "A", "", "Clear"),
                ("Specific Gravity", "1.022", "", "", "1.005-1.030"),
                ("pH", "6.0", "", "", "5.0-8.0"),
                ("Protein", "Trace", "A", "mg/dL", "Negative"),
                ("Glucose", "2+", "A", "", "Negative"),
                ("Ketones", "1+", "A", "", "Negative"),
                ("Blood", "Negative", "", "", "Negative"),
                ("Leukocyte Esterase", "Negative", "", "", "Negative"),
                ("Nitrite", "Negative", "", "", "Negative"),
                ("WBC", "0-2", "", "/HPF", "0-5"),
                ("RBC", "0-1", "", "/HPF", "0-3"),
                ("Bacteria", "None seen", "", "", "None"),
            ]
            y = write_lab_table(c, y, "URINALYSIS WITH MICROSCOPIC", "01/29/2026 20:15", ua_results)
        elif p == 3:
            pod0_results = [
                ("Glucose", "165", "H", "mg/dL", "70-100"),
                ("BUN", "18", "", "mg/dL", "7-20"),
                ("Creatinine", "1.0", "", "mg/dL", "0.7-1.3"),
                ("Sodium", "140", "", "mEq/L", "136-145"),
                ("Potassium", "4.0", "", "mEq/L", "3.5-5.1"),
                ("Chloride", "102", "", "mEq/L", "98-106"),
                ("CO2", "25", "", "mEq/L", "21-32"),
                ("Calcium", "8.9", "", "mg/dL", "8.5-10.5"),
            ]
            y = write_lab_table(c, y, "BASIC METABOLIC PANEL — POD 0", "01/30/2026 16:00", pod0_results)
        elif p == 4:
            pod1_cbc = [
                ("WBC", "11.2", "H", "x10^3/uL", "4.5-11.0"),
                ("RBC", "4.55", "", "x10^6/uL", "4.30-5.90"),
                ("Hemoglobin", "13.8", "", "g/dL", "13.0-17.5"),
                ("Hematocrit", "41.0", "", "%", "38.3-48.6"),
                ("Platelet Count", "275", "", "x10^3/uL", "150-400"),
                ("Neutrophils", "74.0", "H", "%", "40-70"),
            ]
            y = write_lab_table(c, y, "CBC — POST-OP DAY 1", "01/31/2026 06:00", pod1_cbc)
        else:
            dc_bmp = [
                ("Glucose", "142", "H", "mg/dL", "70-100"),
                ("BUN", "16", "", "mg/dL", "7-20"),
                ("Creatinine", "0.9", "", "mg/dL", "0.7-1.3"),
                ("Sodium", "141", "", "mEq/L", "136-145"),
                ("Potassium", "4.3", "", "mEq/L", "3.5-5.1"),
            ]
            y = write_lab_table(c, y, "BASIC METABOLIC PANEL — DISCHARGE", "02/01/2026 06:00", dc_bmp)
        c.showPage()
        page_num += 1

    # ── Radiology (3 pages) ──
    chunk_size = len(radiology_narrative) // 3 + 1
    for p in range(3):
        y = draw_page_header(c, "RADIOLOGY REPORT", page_num)
        start = p * chunk_size
        chunk = radiology_narrative[start:start + chunk_size]
        if p == 1:
            # Add chest x-ray on page 2
            chunk = [
                "CHEST X-RAY — PA AND LATERAL",
                "",
                "PATIENT: Wellington, Charles B.    MRN: RCH-2019-55782",
                "DATE: 01/29/2026    TIME: 19:00 (Pre-operative)",
                "ORDERING PROVIDER: Dr. A. Krishnamurthy, MD",
                "RADIOLOGIST: Dr. Janet Cho, MD",
                "",
                "CLINICAL INDICATION: Pre-operative evaluation, age >65.",
                "",
                "FINDINGS:",
                "Heart size normal. Mediastinal contours unremarkable.",
                "Lungs clear bilaterally. No pleural effusion or pneumothorax.",
                "No acute osseous abnormality. Degenerative changes thoracic spine.",
                "",
                "IMPRESSION: No acute cardiopulmonary process.",
            ]
        if not chunk:
            chunk = ["(Radiology report — see prior page for complete findings)"]
        y, _ = write_text_lines(c, y, chunk)
        if p == 0:
            y -= 10
            c.setFont("Helvetica-Bold", 8)
            c.drawString(50, y, "Electronically signed: Dr. Janet Cho, MD — Diagnostic Radiology")
        c.showPage()
        page_num += 1

    # ── Nursing Notes (8 pages) ──
    for p in range(8):
        y = draw_page_header(c, "NURSING NOTES", page_num)
        if p < len(nursing_note_templates):
            # Wrap long text manually
            note = nursing_note_templates[p]
            words = note.split()
            lines = []
            current_line = ""
            for word in words:
                test = current_line + " " + word if current_line else word
                if len(test) > 80:
                    lines.append(current_line)
                    current_line = word
                else:
                    current_line = test
            if current_line:
                lines.append(current_line)

            c.setFont("Helvetica-Bold", 8)
            dates = ["01/29/2026 19:00", "01/30/2026 02:00", "01/30/2026 06:30",
                     "01/30/2026 11:00", "01/31/2026 07:00", "02/01/2026 07:00",
                     "02/01/2026 14:30", "02/01/2026 14:30"]
            nurses = ["S. Martinez, RN", "T. O'Brien, RN", "S. Martinez, RN",
                      "K. Washington, RN", "S. Martinez, RN", "S. Martinez, RN",
                      "S. Martinez, RN", "S. Martinez, RN"]
            c.drawString(50, y, f"DATE/TIME: {dates[p]}    NURSE: {nurses[p]}")
            y -= 16
            c.setFont("Helvetica", 8)
            for line in lines:
                c.drawString(50, y, line)
                y -= 11
        else:
            # Filler nursing content for pages 7-8
            filler = [
                f"NURSING FLOWSHEET — Continued (Page {p+1})",
                "",
                "Vital Signs Log:",
                "  0600  T 98.4  HR 70  BP 126/72  RR 16  SpO2 98% RA",
                "  1000  T 98.6  HR 74  BP 130/76  RR 16  SpO2 99% RA",
                "  1400  T 98.8  HR 72  BP 128/74  RR 18  SpO2 98% RA",
                "  1800  T 98.6  HR 76  BP 132/78  RR 16  SpO2 98% RA",
                "",
                "Intake/Output:",
                "  PO Intake: 1800 mL",
                "  IV Fluids: Discontinued",
                "  Urine Output: 1400 mL (voiding independently)",
                "",
                "Blood Glucose Log:",
                "  0600: 156 mg/dL (pre-breakfast)",
                "  1200: 178 mg/dL (pre-lunch)",
                "  1800: 142 mg/dL (pre-dinner)",
                "",
                "Pain Assessment:",
                "  0800: 2/10 (acetaminophen given)",
                "  1400: 1/10 (no intervention needed)",
                "  2000: 2/10 (acetaminophen given)",
            ]
            y, _ = write_text_lines(c, y, filler, size=8)

        c.showPage()
        page_num += 1

    # ── Medication Administration Record (4 pages) ──
    entries_per_page = len(mar_entries) // 4 + 1
    for p in range(4):
        y = draw_page_header(c, "MEDICATION ADMINISTRATION RECORD", page_num)
        c.setFont("Helvetica-Bold", 7)
        mar_cols = [50, 140, 300, 400]
        for col, hdr in zip(mar_cols, ["DATE/TIME", "MEDICATION/DOSE/ROUTE", "INDICATION", "NOTES"]):
            c.drawString(col, y, hdr)
        y -= 4
        c.line(50, y, W - 50, y)
        y -= 11

        c.setFont("Helvetica", 7)
        start = p * entries_per_page
        chunk = mar_entries[start:start + entries_per_page]
        for dt, med, ind, notes in chunk:
            c.drawString(50, y, dt)
            c.drawString(140, y, med)
            c.drawString(300, y, ind)
            c.drawString(400, y, notes)
            y -= 10

        if not chunk:
            c.setFont("Helvetica", 8)
            c.drawString(50, y, "(MAR continued — routine medication administration documented)")
            y -= 12
            c.drawString(50, y, "All medications administered as ordered. No adverse reactions noted.")

        c.showPage()
        page_num += 1

    # ── Discharge Instructions (2 pages) ──
    chunk_size = len(discharge_instructions) // 2 + 1
    for p in range(2):
        y = draw_page_header(c, "DISCHARGE INSTRUCTIONS", page_num)
        start = p * chunk_size
        chunk = discharge_instructions[start:start + chunk_size]
        y, _ = write_text_lines(c, y, chunk)
        if p == 1:
            y -= 14
            c.setFont("Helvetica-Bold", 8)
            c.drawString(50, y, "Patient Signature: ________________________________  Date: 02/01/2026")
            y -= 14
            c.drawString(50, y, "Witness: S. Martinez, RN                            Date: 02/01/2026")
        c.showPage()
        page_num += 1

    c.save()
    print(f"    Chart dump: {page_num - 1} pages generated")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT 11: Illegible Physician Handwritten Notes
# Simulates a handwritten note that was faxed — the kind where the
# scanner barely picked up the ink. Uses irregular, cramped text
# placement, light color, and overlapping lines to simulate illegibility.
# ═══════════════════════════════════════════════════════════════════════════

def create_illegible_notes():
    path = os.path.join(OUTPUT_DIR, "11_illegible_physician_notes.pdf")
    c = canvas.Canvas(path, pagesize=letter)

    # Fax transmission header
    c.setFont("Courier", 7)
    c.drawString(36, H - 18,
        "02/09/2026 11:23AM  FROM: (555) 441-8800  DR PATEL INTERNAL MED  TO: (555) 867-5309  P.01/01")

    # The "handwritten" note — we simulate this with:
    # 1. Light gray text (faded ink on fax)
    # 2. Slightly varying y-positions (uneven lines)
    # 3. A mix of readable and deliberately garbled text
    # 4. No clean structure

    # First: a pre-printed prescription pad / note template at the top
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(HexColor("#444444"))
    c.drawCentredString(W / 2, H - 50, "RAJESH PATEL, MD — INTERNAL MEDICINE")
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor("#666666"))
    c.drawCentredString(W / 2, H - 62, "4455 Elm Street, Suite 3B  |  Willowdale, OR 97333")
    c.drawCentredString(W / 2, H - 73, "Phone: (555) 441-8800  |  Fax: (555) 441-8801  |  NPI: 5556667778")

    c.setStrokeColor(HexColor("#888888"))
    c.line(40, H - 80, W - 40, H - 80)

    # Pre-printed fields partially filled in by "hand"
    y = H - 100
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#666666"))
    c.drawString(40, y, "Date: ____________    Patient: ________________________________    DOB: ____________")

    # "Handwritten" fill-ins — lighter, slightly offset, irregular font
    # We'll use Courier to look different from the printed template
    c.setFillColor(HexColor("#3a3a3a"))
    c.setFont("Courier", 9)
    c.drawString(76, y + 1, "2/8/26")
    c.drawString(212, y - 1, "Gonzalez, Maria T")
    c.drawString(472, y + 1, "6/14/80")

    y -= 22
    c.setFillColor(HexColor("#666666"))
    c.setFont("Helvetica", 9)
    c.drawString(40, y, "RE: ___________________________________________________________________________")

    c.setFillColor(HexColor("#3a3a3a"))
    c.setFont("Courier", 9)
    c.drawString(65, y + 1, "F/U visit - HTN mgmt, DM control, knee pain")

    y -= 30
    c.setStrokeColor(HexColor("#888888"))
    c.line(40, y, W - 40, y)
    y -= 10

    # Now the "handwritten" clinical note
    # Use very light color + slight position jitter to simulate bad fax of handwriting
    random.seed(77)

    handwritten_lines = [
        "Dr Sato -",
        "",
        "Pt seen today for f/u. BP 148/92 today, was 152/96 last",
        "visit. On lisinopril 10mg, not at goal. Will inc to 20mg.",
        "Discussed low-Na diet, pt states compliance is 'ok'.",
        "",
        "DM: A1c 7.8 (was 8.1 in Oct). Cont metformin 1000 BID.",
        "Discussed adding GLP-1 vs increasing met dose.",  
        "Pt prefers to try diet changes x 3mo before adding",
        "new med. Will recheck A1c in May.",
        "",
        "R knee: Worse x 2 wks. Crepitus on exam, ROM limited",
        "~100 deg flexion (was 120). XR today shows mod DJD",
        "medial compartment, no loose bodies. Rec PT eval +",
        "trial of meloxicam 15mg daily x 30d. If no improvement",
        "will refer to ortho.",
        "",
        "Labs ordered: CMP, lipid panel, A1c (May), UA",
        "",
        "Meds updated:",
        "  - Lisinopril 10mg -> 20mg daily",
        "  - Add meloxicam 15mg daily x 30d",
        "  - Cont metformin 1000 BID",
        "  - Cont atorvastatin 20mg QHS",
        "",
        "RTC 3 months or sooner if BP not improving",
        "",
        "Pls note - I am moving my practice to new location",
        "eff 4/1/26. New addr will be 8200 Cedar Ln Ste 100.",
        "Same phone/fax. Will send formal notice.",
        "",
        "Thanks,",
        "R. Patel",
    ]

    for line in handwritten_lines:
        if line == "":
            y -= 10
            continue

        # Simulate handwriting: jitter position, use light color, Courier font
        x_jitter = random.uniform(-2, 3)
        y_jitter = random.uniform(-1.5, 1.5)

        # Vary opacity to simulate faded ink
        shade = random.choice(["#2d2d2d", "#3a3a3a", "#444444", "#4d4d4d", "#555555"])
        c.setFillColor(HexColor(shade))

        # Some lines use slightly different sizes (pressure variation)
        size = random.choice([8.5, 9, 9, 9, 9.5])
        c.setFont("Courier", size)
        c.drawString(50 + x_jitter, y + y_jitter, line)
        y -= 14

    # Add some "smudges" and artifacts typical of faxed handwritten notes
    # Light gray blobs
    for _ in range(12):
        x = random.uniform(40, W - 40)
        yy = random.uniform(100, H - 120)
        c.setFillColor(HexColor("#00000015"))
        c.circle(x, yy, random.uniform(1, 4), fill=True, stroke=False)

    # A diagonal line simulating where the paper was folded
    c.setStrokeColor(HexColor("#00000012"))
    c.setLineWidth(0.5)
    c.line(60, H - 300, W - 80, H - 280)

    c.save()
    add_scan_artifacts(path, path, noise_level="heavy")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT 12: Wrong Provider — Misdirected Fax
# A physical therapy referral order that was sent to the primary care
# office instead of the PT clinic. This tests whether the classifier
# can identify that the document is not intended for this practice.
# ═══════════════════════════════════════════════════════════════════════════

def create_wrong_provider():
    path = os.path.join(OUTPUT_DIR, "12_wrong_provider_misdirected.pdf")
    c = canvas.Canvas(path, pagesize=letter)

    # Fax header — note the TO line shows the wrong fax number
    c.setFont("Courier", 7)
    c.drawString(36, H - 18,
        "02/13/2026 14:07PM  FROM: SUMMIT ORTHO (555) 776-4400  TO: (555) 867-5309  P.01/02")

    # This is an orthopedic surgeon's office sending a PT referral
    # But they faxed it to the PCP office (555-867-5309) instead of
    # the PT clinic (555-867-5310 — off by one digit)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(36, H - 50, "SUMMIT ORTHOPEDICS & SPORTS MEDICINE")
    c.setFont("Helvetica", 8)
    c.drawString(36, H - 62, "Dr. Marcus Bellingham, MD  |  Dr. Priya Venkatesh, MD")
    c.drawString(36, H - 72, "3100 Lakewood Drive, Suite 210  |  Meadowbrook, CO 80555")
    c.drawString(36, H - 82, "Phone: (555) 776-4400  |  Fax: (555) 776-4401")

    c.line(36, H - 90, W - 36, H - 90)

    y = H - 110

    # Cover/routing info — clearly addressed to a PT clinic, not this office
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W / 2, y, "PHYSICAL THERAPY REFERRAL ORDER")
    y -= 24

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "TO:")
    c.setFont("Helvetica", 10)
    c.drawString(90, y, "Willowdale Physical Therapy & Rehabilitation")
    y -= 14
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "FAX:")
    c.setFont("Helvetica", 10)
    c.drawString(90, y, "(555) 867-5310")   # <-- note: off by one from the PCP fax
    y -= 14
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "ATTN:")
    c.setFont("Helvetica", 10)
    c.drawString(90, y, "Physical Therapy Intake Coordinator")
    y -= 14
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "FROM:")
    c.setFont("Helvetica", 10)
    c.drawString(90, y, "Dr. Marcus Bellingham, MD — Summit Orthopedics")
    y -= 14
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "DATE:")
    c.setFont("Helvetica", 10)
    c.drawString(90, y, "February 13, 2026")

    y -= 22
    c.line(50, y, W - 50, y)
    y -= 18

    # Patient info
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "PATIENT INFORMATION")
    y -= 16
    pt_fields = [
        ("Patient Name:", "KOWALSKI, ADAM J."),
        ("Date of Birth:", "05/19/1988"),
        ("Phone:", "(555) 744-2211"),
        ("Insurance:", "Pinnacle Health Plans — Gold PPO"),
        ("Member ID:", "PHP-117-55-3342"),
        ("Authorization #:", "PA-2026-0210-55490 (APPROVED — see attached)"),
    ]
    for label, val in pt_fields:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(60, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(175, y, val)
        y -= 14

    y -= 8
    c.line(50, y, W - 50, y)
    y -= 18

    # Clinical info
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "DIAGNOSIS / CLINICAL INFORMATION")
    y -= 16
    clinical = [
        ("Primary Dx:", "M23.211 — Derangement of anterior horn of medial meniscus, right knee"),
        ("Secondary Dx:", "M17.11 — Primary osteoarthritis, right knee"),
        ("Date of Injury/Onset:", "01/08/2026 (work-related, bending/twisting injury)"),
        ("Surgical History:", "None — conservative management first"),
        ("Imaging:", "MRI R knee (02/03/2026): Medial meniscus tear, grade II chondromalacia"),
    ]
    for label, val in clinical:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(60, y, label)
        c.setFont("Helvetica", 8)
        c.drawString(175, y, val)
        y -= 14

    y -= 8
    c.line(50, y, W - 50, y)
    y -= 18

    # PT Order
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "PHYSICAL THERAPY ORDER")
    y -= 18

    c.setFont("Helvetica", 9)
    order_lines = [
        "Evaluate and treat: Right knee — meniscal tear, OA",
        "",
        "Frequency/Duration: 2-3x/week for 6 weeks (12-18 sessions)",
        "",
        "Goals:",
        "  1. Reduce pain to 3/10 or less (currently 6/10)",
        "  2. Restore full ROM (currently limited 10-110 deg, goal 0-135)",
        "  3. Strengthen quadriceps and hamstrings to 4+/5",
        "  4. Return to full work duties (warehouse — lifting, bending, walking)",
        "",
        "Precautions:",
        "  - No deep squatting or high-impact activity",
        "  - No pivoting on affected leg",
        "  - Weight bearing as tolerated",
        "",
        "Treatment may include:",
        "  Therapeutic exercise, manual therapy, neuromuscular re-education,",
        "  modalities (ice, e-stim, ultrasound PRN), functional training,",
        "  home exercise program development",
        "",
        "Please fax initial evaluation and progress notes to our office:",
        "  Fax: (555) 776-4401  ATTN: Dr. Bellingham",
        "",
        "If patient is not progressing by week 4, please contact our office",
        "to discuss. May need to consider surgical consultation at that point.",
    ]
    for line in order_lines:
        if line == "":
            y -= 6
            continue
        if line.startswith("  "):
            c.drawString(65, y, line.strip())
        elif line.endswith(":"):
            c.setFont("Helvetica-Bold", 9)
            c.drawString(50, y, line)
            c.setFont("Helvetica", 9)
        else:
            c.drawString(50, y, line)
        y -= 12

    y -= 16
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "Ordering Physician: Marcus Bellingham, MD  |  NPI: 1234509876")
    y -= 12
    c.drawString(50, y, "Electronically signed: 02/13/2026")

    y -= 30
    c.setFont("Helvetica", 7)
    c.drawString(50, y, "CONFIDENTIALITY: This fax contains PHI intended for Willowdale Physical Therapy.")
    y -= 10
    c.drawString(50, y, "If received in error, please notify Summit Orthopedics at (555) 776-4400 and destroy all copies.")

    # Page 2: The attached prior auth approval
    c.showPage()

    c.setFont("Courier", 7)
    c.drawString(36, H - 18,
        "02/13/2026 14:07PM  FROM: SUMMIT ORTHO (555) 776-4400  TO: (555) 867-5309  P.02/02")

    c.setFont("Helvetica-Bold", 13)
    c.drawString(36, H - 50, "PINNACLE HEALTH PLANS")
    c.setFont("Helvetica", 8)
    c.drawString(36, H - 62, "Utilization Management Department")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(W - 36, H - 50, "PRIOR AUTHORIZATION")
    c.drawRightString(W - 36, H - 63, "DETERMINATION NOTICE")
    c.setFont("Courier-Bold", 9)
    c.drawRightString(W - 36, H - 78, "Auth #: PA-2026-0210-55490")

    c.line(36, H - 86, W - 36, H - 86)

    y = H - 106
    c.setFont("Helvetica", 9)
    c.drawString(36, y, "Date: February 10, 2026")
    y -= 14
    c.drawString(36, y, "Member: KOWALSKI, ADAM J.  |  ID: PHP-117-55-3342  |  DOB: 05/19/1988")
    y -= 14
    c.drawString(36, y, "Service: Physical Therapy, Right Knee (CPT 97110, 97140, 97530)")
    y -= 14
    c.drawString(36, y, "Provider: Willowdale Physical Therapy & Rehabilitation")
    y -= 14
    c.drawString(36, y, "Approved: 18 visits over 6 weeks, effective 02/10/2026 through 03/24/2026")
    y -= 22

    c.setFont("Helvetica-Bold", 12)
    c.drawString(36, y, "DETERMINATION: ")
    c.rect(170, y - 3, 12, 12, fill=False)
    c.drawString(172, y - 1, "X")
    c.setFillColor(HexColor("#006600"))
    c.drawString(188, y, "APPROVED")
    c.setFillColor(black)

    y -= 30
    c.setFont("Helvetica", 8)
    c.drawString(36, y, "This authorization is valid for the dates and services listed above.")
    y -= 12
    c.drawString(36, y, "Pre-certification does not guarantee payment. Benefits subject to plan terms and conditions.")

    c.save()
    add_scan_artifacts(path, path, noise_level="light")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Generating edge-case synthetic healthcare fax documents...\n")

    generators = [
        ("09 - Orphan Cover Page (no content)", create_orphan_cover_page),
        ("10 - Chart Dump (40 pages)", create_chart_dump),
        ("11 - Illegible Physician Notes", create_illegible_notes),
        ("12 - Wrong Provider (misdirected PT referral)", create_wrong_provider),
    ]

    created_files = []
    for name, gen_fn in generators:
        try:
            filepath = gen_fn()
            created_files.append(filepath)
            print(f"  [OK] {name}")
            print(f"       -> {filepath}")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"Generated {len(created_files)} of {len(generators)} edge-case documents")
    print(f"{'='*60}")
