#!/usr/bin/env python3
"""
Generate 8 synthetic healthcare fax PDFs for Fax Capacitor testing.
Each document uses clearly fictional data, varied formatting, and
realistic layouts to test AI classification pipelines.
"""

import os
import random
import math
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import black, gray, lightgrey, white, HexColor, red
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from pypdf import PdfReader, PdfWriter
import io

OUTPUT_DIR = "/home/claude/faxes"
os.makedirs(OUTPUT_DIR, exist_ok=True)

W, H = letter  # 612 x 792

# ─── Helpers ───────────────────────────────────────────────────────────────

def fax_header(c, from_name, from_fax, to_name, to_fax, date, pages, re_line=None, y_start=None):
    """Draw a standard fax cover-sheet style header band."""
    y = y_start or (H - 60)
    c.setFont("Courier", 8)
    c.drawString(36, H - 20, f"FAX TRANSMISSION  —  {date}  —  Page 1 of {pages}")
    c.setFont("Helvetica", 9)
    c.drawString(36, y, f"FROM: {from_name}")
    c.drawString(36, y - 12, f"FAX:  {from_fax}")
    c.drawString(320, y, f"TO: {to_name}")
    c.drawString(320, y - 12, f"FAX: {to_fax}")
    if re_line:
        c.drawString(36, y - 28, f"RE: {re_line}")
        y -= 40
    else:
        y -= 28
    c.line(36, y, W - 36, y)
    return y - 14


def apply_slight_rotation(input_path, output_path, angle_deg):
    """Rotate pages slightly to simulate a skewed scan."""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        # pypdf only supports 90-degree increments natively,
        # so we'll use a different approach — we stamp the content
        # onto a slightly rotated canvas using reportlab.
        writer.add_page(page)
    writer.write(open(output_path, "wb"))


def add_scan_artifacts(input_path, output_path, noise_level="light"):
    """Overlay light gray speckles and a faint edge shadow to simulate scanning."""
    reader = PdfReader(input_path)
    # Create an overlay PDF with noise
    overlay_buf = io.BytesIO()
    oc = canvas.Canvas(overlay_buf, pagesize=letter)
    random.seed(42)  # reproducible

    if noise_level == "heavy":
        # Heavier gray wash + more speckles
        oc.setFillColor(HexColor("#00000008"))
        oc.rect(0, 0, W, H, fill=True, stroke=False)
        # Edge darkening
        oc.setFillColor(HexColor("#00000012"))
        oc.rect(0, 0, 18, H, fill=True, stroke=False)
        oc.rect(W - 18, 0, 18, H, fill=True, stroke=False)
        # Random speckles
        for _ in range(60):
            x = random.uniform(20, W - 20)
            y = random.uniform(20, H - 20)
            oc.setFillColor(HexColor("#00000018"))
            oc.circle(x, y, random.uniform(0.3, 1.2), fill=True, stroke=False)
    else:
        # Light artifacts
        for _ in range(15):
            x = random.uniform(20, W - 20)
            y = random.uniform(20, H - 20)
            oc.setFillColor(HexColor("#00000010"))
            oc.circle(x, y, random.uniform(0.2, 0.8), fill=True, stroke=False)

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
# DOCUMENT 1: Lab Result — CBC Panel
# Clean, professional clinical lab format
# ═══════════════════════════════════════════════════════════════════════════

def create_lab_result():
    path = os.path.join(OUTPUT_DIR, "01_lab_result_cbc.pdf")
    c = canvas.Canvas(path, pagesize=letter)

    # Lab letterhead
    c.setFont("Helvetica-Bold", 14)
    c.drawString(36, H - 40, "SUMMIT VALLEY REFERENCE LABORATORY")
    c.setFont("Helvetica", 8)
    c.drawString(36, H - 52, "4200 Ridgecrest Blvd, Suite 110  |  Meadowbrook, CO 80555")
    c.drawString(36, H - 62, "Phone: (555) 234-7890  |  Fax: (555) 234-7891  |  CLIA# 05D9876543")

    c.line(36, H - 70, W - 36, H - 70)

    # Fax transmission line
    c.setFont("Courier", 7)
    c.drawString(36, H - 82, "FAX TRANSMISSION: 01/28/2026 14:32  TO: (555) 867-5309  Whispering Pines Family Medicine")

    c.line(36, H - 88, W - 36, H - 88)

    # Patient info block
    y = H - 108
    c.setFont("Helvetica-Bold", 10)
    c.drawString(36, y, "LABORATORY REPORT — COMPLETE BLOOD COUNT (CBC) WITH DIFFERENTIAL")
    y -= 20

    info = [
        ("Patient:", "THORNBERRY, MARGARET A.", "DOB:", "04/15/1958"),
        ("MRN:", "MRN-20260128-4471", "Sex:", "Female"),
        ("Ordering Physician:", "Dr. Evelyn Sato, DO", "Collection Date:", "01/27/2026 08:15"),
        ("Account #:", "ACCT-88321", "Report Date:", "01/28/2026 13:47"),
    ]

    c.setFont("Helvetica", 8)
    for label1, val1, label2, val2 in info:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(36, y, label1)
        c.setFont("Helvetica", 8)
        c.drawString(130, y, val1)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(360, y, label2)
        c.setFont("Helvetica", 8)
        c.drawString(460, y, val2)
        y -= 13

    y -= 8
    c.line(36, y, W - 36, y)
    y -= 14

    # Results table header
    c.setFont("Helvetica-Bold", 8)
    cols = [36, 200, 280, 340, 420, 500]
    headers = ["TEST", "RESULT", "FLAG", "UNITS", "REFERENCE RANGE", "STATUS"]
    for col, hdr in zip(cols, headers):
        c.drawString(col, y, hdr)
    y -= 4
    c.line(36, y, W - 36, y)
    y -= 13

    # Results
    results = [
        ("WBC", "11.8", "H", "x10^3/uL", "4.5 - 11.0", "Final"),
        ("RBC", "4.52", "", "x10^6/uL", "3.80 - 5.10", "Final"),
        ("Hemoglobin", "13.1", "", "g/dL", "12.0 - 16.0", "Final"),
        ("Hematocrit", "39.2", "", "%", "36.0 - 46.0", "Final"),
        ("MCV", "86.7", "", "fL", "80.0 - 100.0", "Final"),
        ("MCH", "29.0", "", "pg", "27.0 - 33.0", "Final"),
        ("MCHC", "33.4", "", "g/dL", "32.0 - 36.0", "Final"),
        ("RDW", "13.5", "", "%", "11.5 - 14.5", "Final"),
        ("Platelet Count", "245", "", "x10^3/uL", "150 - 400", "Final"),
        ("MPV", "9.8", "", "fL", "7.5 - 12.5", "Final"),
        ("", "", "", "", "", ""),
        ("DIFFERENTIAL", "", "", "", "", ""),
        ("Neutrophils", "72.1", "H", "%", "40.0 - 70.0", "Final"),
        ("Lymphocytes", "18.4", "", "%", "20.0 - 45.0", "Final"),
        ("Monocytes", "6.2", "", "%", "2.0 - 10.0", "Final"),
        ("Eosinophils", "2.8", "", "%", "1.0 - 6.0", "Final"),
        ("Basophils", "0.5", "", "%", "0.0 - 2.0", "Final"),
        ("Abs Neutrophils", "8.51", "H", "x10^3/uL", "1.80 - 7.70", "Final"),
        ("Abs Lymphocytes", "2.17", "", "x10^3/uL", "1.00 - 4.80", "Final"),
        ("Abs Monocytes", "0.73", "", "x10^3/uL", "0.10 - 1.00", "Final"),
    ]

    c.setFont("Helvetica", 8)
    for test, result, flag, units, ref, status in results:
        if test == "DIFFERENTIAL":
            c.setFont("Helvetica-Bold", 8)
            c.drawString(36, y, test)
            c.setFont("Helvetica", 8)
            y -= 13
            continue
        if test == "":
            y -= 6
            continue
        c.drawString(36, y, test)
        if flag == "H":
            c.setFillColor(red)
            c.setFont("Helvetica-Bold", 8)
        c.drawString(200, y, result)
        c.drawString(280, y, flag)
        c.setFillColor(black)
        c.setFont("Helvetica", 8)
        c.drawString(340, y, units)
        c.drawString(420, y, ref)
        c.drawString(500, y, status)
        y -= 13

    y -= 12
    c.line(36, y, W - 36, y)
    y -= 14

    # Comment
    c.setFont("Helvetica-Bold", 8)
    c.drawString(36, y, "COMMENT:")
    c.setFont("Helvetica", 8)
    y -= 12
    c.drawString(36, y, "WBC and absolute neutrophil count mildly elevated. Clinical correlation recommended.")
    y -= 12
    c.drawString(36, y, "Suggest repeat CBC in 2-4 weeks if clinically indicated.")

    y -= 30
    c.setFont("Helvetica-Bold", 8)
    c.drawString(36, y, "Reviewed & Released by: James T. Nakamura, MD, PhD — Laboratory Director")
    y -= 12
    c.setFont("Helvetica", 7)
    c.drawString(36, y, "This report is intended for the ordering provider. If received in error, please notify Summit Valley Reference Lab immediately.")

    c.save()
    return path


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT 2: Referral Response — Cardiology Consult
# Slightly "faded" appearance
# ═══════════════════════════════════════════════════════════════════════════

def create_referral_response():
    path = os.path.join(OUTPUT_DIR, "02_referral_response_cardiology.pdf")
    c = canvas.Canvas(path, pagesize=letter)

    # Use slightly lighter text to simulate faded fax
    text_color = HexColor("#2a2a2a")
    c.setFillColor(text_color)

    # Letterhead
    c.setFont("Times-Bold", 16)
    c.drawCentredString(W / 2, H - 45, "HEARTLAND CARDIOLOGY ASSOCIATES")
    c.setFont("Times-Roman", 9)
    c.drawCentredString(W / 2, H - 58, "Rebecca Okonkwo, MD, FACC  |  Samuel Pfeiffer, MD, FACC  |  Anya Deshmukh, MD")
    c.drawCentredString(W / 2, H - 70, "7700 Cardiac Care Drive, Suite 400  •  Willowdale, OR 97333")
    c.drawCentredString(W / 2, H - 82, "Tel: (555) 443-2100  •  Fax: (555) 443-2101")

    c.setStrokeColor(text_color)
    c.line(50, H - 90, W - 50, H - 90)

    # Fax header info
    y = H - 110
    c.setFont("Helvetica", 9)
    c.drawString(50, y, "Date: February 3, 2026")
    c.drawString(350, y, "Pages: 1 of 1 (including cover)")
    y -= 16
    c.drawString(50, y, "TO: Dr. Evelyn Sato, DO — Whispering Pines Family Medicine")
    y -= 14
    c.drawString(50, y, "FAX: (555) 867-5309")
    y -= 14
    c.drawString(50, y, "FROM: Dr. Rebecca Okonkwo, MD, FACC")
    y -= 14
    c.drawString(50, y, "RE: Consultation — THORNBERRY, MARGARET A. (DOB 04/15/1958)")

    y -= 20
    c.line(50, y, W - 50, y)
    y -= 18

    # Letter body
    c.setFont("Times-Roman", 10)
    lines = [
        "Dear Dr. Sato,",
        "",
        "Thank you for referring Mrs. Thornberry for cardiology evaluation. I had the",
        "pleasure of seeing her in our clinic on January 31, 2026.",
        "",
        "CHIEF COMPLAINT: Intermittent palpitations and exertional dyspnea over the",
        "past 3 months.",
        "",
        "EVALUATION PERFORMED:",
        "  - 12-lead ECG: Normal sinus rhythm, rate 74 bpm, no ST changes",
        "  - Transthoracic Echocardiogram: LVEF 60%, no valvular abnormalities,",
        "    normal chamber dimensions",
        "  - 48-hour Holter Monitor: Ordered, results pending (est. 2 weeks)",
        "",
        "IMPRESSION:",
        "At this time, the structural evaluation is reassuring. The echocardiogram is",
        "normal and there is no evidence of significant valvular disease or systolic",
        "dysfunction. The Holter monitor will help characterize the arrhythmia burden.",
        "",
        "PLAN:",
        "  1. Await Holter results — will fax addendum upon receipt",
        "  2. Start low-dose metoprolol 25mg daily for symptom management",
        "  3. Recommend thyroid panel if not recently checked (TSH, Free T4)",
        "  4. Follow-up in 4-6 weeks after Holter review",
        "",
        "I will keep you informed of the Holter findings. Please do not hesitate to",
        "contact our office with any questions.",
        "",
        "Sincerely,",
        "",
        "",
        "Rebecca Okonkwo, MD, FACC",
        "Heartland Cardiology Associates",
    ]

    for line in lines:
        c.drawString(50, y, line)
        y -= 13

    y -= 10
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#555555"))
    c.drawString(50, y, "CONFIDENTIALITY NOTICE: This fax contains protected health information (PHI) intended only for the")
    y -= 10
    c.drawString(50, y, "named recipient. If received in error, please notify sender immediately and destroy all copies.")

    c.save()
    # Add faded/scan artifacts
    add_scan_artifacts(path, path, noise_level="heavy")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT 3: Prior Authorization Decision — APPROVED
# Insurance company format with checkboxes
# ═══════════════════════════════════════════════════════════════════════════

def create_prior_auth_approved():
    path = os.path.join(OUTPUT_DIR, "03_prior_auth_approved.pdf")
    c = canvas.Canvas(path, pagesize=letter)

    # Company header
    c.setFont("Helvetica-Bold", 13)
    c.drawString(36, H - 40, "PINNACLE HEALTH PLANS")
    c.setFont("Helvetica", 8)
    c.drawString(36, H - 52, "Utilization Management Department")
    c.drawString(36, H - 62, "P.O. Box 99100, Silverstone, TX 75001")
    c.drawString(36, H - 72, "Phone: 1-800-555-0147  |  Fax: 1-800-555-0148")
    c.drawString(36, H - 82, "www.pinnaclehealthplans.example.com")

    # Right side: Auth reference
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(W - 36, H - 45, "PRIOR AUTHORIZATION")
    c.drawRightString(W - 36, H - 58, "DETERMINATION NOTICE")
    c.setFont("Courier-Bold", 9)
    c.drawRightString(W - 36, H - 75, "Auth #: PA-2026-0128-55321")

    c.line(36, H - 90, W - 36, H - 90)

    y = H - 110
    c.setFont("Helvetica", 9)

    # Date and routing
    c.drawString(36, y, "Date of Determination: January 30, 2026")
    y -= 16
    c.drawString(36, y, "TO:  Whispering Pines Family Medicine  /  Fax: (555) 867-5309")
    y -= 14
    c.drawString(36, y, "ATTN: Dr. Evelyn Sato, DO")
    y -= 20

    c.line(36, y, W - 36, y)
    y -= 16

    # Member info
    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, y, "MEMBER INFORMATION")
    y -= 14
    c.setFont("Helvetica", 9)
    member_info = [
        ("Member Name:", "DELACROIX, THOMAS R."),
        ("Member ID:", "PHP-882-44-6712"),
        ("Date of Birth:", "09/22/1971"),
        ("Group #:", "GRP-MEDWEST-4400"),
        ("Plan:", "Pinnacle Gold PPO"),
    ]
    for label, val in member_info:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(50, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(150, y, val)
        y -= 13

    y -= 8
    c.line(36, y, W - 36, y)
    y -= 16

    # Service requested
    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, y, "SERVICE REQUESTED")
    y -= 14
    svc_info = [
        ("Procedure:", "MRI Lumbar Spine without Contrast (CPT 72148)"),
        ("Diagnosis:", "M54.5 — Low back pain; M51.16 — Lumbar disc degeneration"),
        ("Facility:", "Crestview Imaging Center — NPI 1234567890"),
        ("Requested by:", "Dr. Evelyn Sato, DO — NPI 9876543210"),
        ("Date of Service:", "On or before 03/01/2026"),
    ]
    c.setFont("Helvetica", 9)
    for label, val in svc_info:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(50, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(150, y, val)
        y -= 13

    y -= 10
    c.line(36, y, W - 36, y)
    y -= 18

    # DETERMINATION — big bold box
    c.setFont("Helvetica-Bold", 12)
    c.drawString(36, y, "DETERMINATION:")

    # Checkbox style
    # Approved ☑
    c.rect(180, y - 3, 12, 12, fill=False)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(182, y - 1, "X")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(HexColor("#006600"))
    c.drawString(198, y, "APPROVED")
    c.setFillColor(black)

    y -= 18
    # Denied ☐
    c.rect(180, y - 3, 12, 12, fill=False)
    c.setFont("Helvetica", 11)
    c.drawString(198, y, "DENIED")
    y -= 18
    # Partial ☐
    c.rect(180, y - 3, 12, 12, fill=False)
    c.drawString(198, y, "PARTIALLY APPROVED")
    y -= 18
    # Pend ☐
    c.rect(180, y - 3, 12, 12, fill=False)
    c.drawString(198, y, "PENDED FOR ADDITIONAL INFORMATION")

    y -= 22
    c.line(36, y, W - 36, y)
    y -= 16

    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, y, "NOTES:")
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(50, y, "Authorization valid for 60 days from date of determination.")
    y -= 13
    c.drawString(50, y, "One (1) MRI Lumbar Spine without contrast approved at Crestview Imaging Center.")
    y -= 13
    c.drawString(50, y, "Pre-certification does not guarantee payment. Benefits subject to plan terms.")

    y -= 30
    c.setFont("Helvetica", 8)
    c.drawString(36, y, "Reviewed by: Lisa Chang, RN — Utilization Review Coordinator")
    y -= 12
    c.drawString(36, y, "Medical Director: Dr. Howard P. Gaines, MD, MBA")

    y -= 24
    c.setFont("Helvetica", 7)
    c.drawString(36, y, "If you disagree with this determination, you or the member may file an appeal within 180 days.")
    y -= 10
    c.drawString(36, y, "Appeal requests: Pinnacle Health Plans, Attn: Appeals Dept, PO Box 99200, Silverstone, TX 75001  Fax: 1-800-555-0149")

    c.save()
    return path


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT 4: Prior Authorization Decision — DENIED
# Same insurer, different patient, DENIED
# ═══════════════════════════════════════════════════════════════════════════

def create_prior_auth_denied():
    path = os.path.join(OUTPUT_DIR, "04_prior_auth_denied.pdf")
    c = canvas.Canvas(path, pagesize=letter)

    # Same insurer header
    c.setFont("Helvetica-Bold", 13)
    c.drawString(36, H - 40, "PINNACLE HEALTH PLANS")
    c.setFont("Helvetica", 8)
    c.drawString(36, H - 52, "Utilization Management Department")
    c.drawString(36, H - 62, "P.O. Box 99100, Silverstone, TX 75001")
    c.drawString(36, H - 72, "Phone: 1-800-555-0147  |  Fax: 1-800-555-0148")

    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(W - 36, H - 45, "PRIOR AUTHORIZATION")
    c.drawRightString(W - 36, H - 58, "DETERMINATION NOTICE")
    c.setFont("Courier-Bold", 9)
    c.drawRightString(W - 36, H - 75, "Auth #: PA-2026-0204-55487")

    c.line(36, H - 90, W - 36, H - 90)

    y = H - 110
    c.setFont("Helvetica", 9)
    c.drawString(36, y, "Date of Determination: February 4, 2026")
    y -= 16
    c.drawString(36, y, "TO:  Whispering Pines Family Medicine  /  Fax: (555) 867-5309")
    y -= 14
    c.drawString(36, y, "ATTN: Dr. Evelyn Sato, DO")
    y -= 20
    c.line(36, y, W - 36, y)
    y -= 16

    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, y, "MEMBER INFORMATION")
    y -= 14
    member_info = [
        ("Member Name:", "JOHANSSON, ASTRID K."),
        ("Member ID:", "PHP-331-72-8899"),
        ("Date of Birth:", "12/03/1985"),
        ("Group #:", "GRP-TECHSERV-2200"),
        ("Plan:", "Pinnacle Silver HMO"),
    ]
    c.setFont("Helvetica", 9)
    for label, val in member_info:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(50, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(150, y, val)
        y -= 13

    y -= 8
    c.line(36, y, W - 36, y)
    y -= 16

    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, y, "SERVICE REQUESTED")
    y -= 14
    svc_info = [
        ("Procedure:", "Lumbar Epidural Steroid Injection (CPT 62323)"),
        ("Diagnosis:", "M54.5 — Low back pain; M54.41 — Lumbosacral radiculopathy"),
        ("Facility:", "Prairie Pain Management — NPI 5551234567"),
        ("Requested by:", "Dr. Evelyn Sato, DO — NPI 9876543210"),
    ]
    for label, val in svc_info:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(50, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(150, y, val)
        y -= 13

    y -= 10
    c.line(36, y, W - 36, y)
    y -= 18

    c.setFont("Helvetica-Bold", 12)
    c.drawString(36, y, "DETERMINATION:")

    # Approved ☐
    c.rect(180, y - 3, 12, 12, fill=False)
    c.setFont("Helvetica", 11)
    c.drawString(198, y, "APPROVED")
    y -= 18
    # Denied ☑
    c.rect(180, y - 3, 12, 12, fill=False)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(182, y - 1, "X")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(red)
    c.drawString(198, y, "DENIED")
    c.setFillColor(black)
    y -= 18
    c.rect(180, y - 3, 12, 12, fill=False)
    c.setFont("Helvetica", 11)
    c.drawString(198, y, "PARTIALLY APPROVED")
    y -= 18
    c.rect(180, y - 3, 12, 12, fill=False)
    c.drawString(198, y, "PENDED FOR ADDITIONAL INFORMATION")

    y -= 22
    c.line(36, y, W - 36, y)
    y -= 16

    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, y, "REASON FOR DENIAL:")
    y -= 14
    c.setFont("Helvetica", 9)
    reasons = [
        "The request does not meet medical necessity criteria per Pinnacle Clinical Policy CP-2024-SPINE-03.",
        "Documentation submitted does not demonstrate completion of conservative therapy for a minimum",
        "of 6 weeks, including physical therapy (minimum 6 sessions) and trial of at least two different",
        "oral analgesic/anti-inflammatory medications.",
        "",
        "Clinical Rationale: Submitted records indicate only 2 weeks of home exercise instruction.",
        "No formal physical therapy referral documented. Only one NSAID trial documented (naproxen).",
    ]
    for line in reasons:
        c.drawString(50, y, line)
        y -= 12

    y -= 10
    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, y, "TO SATISFY THIS REQUEST, PLEASE SUBMIT:")
    y -= 14
    c.setFont("Helvetica", 9)
    items = [
        "1. Documentation of completed formal physical therapy (minimum 6 sessions over 6+ weeks)",
        "2. Trial of second-line analgesic or muscle relaxant (in addition to naproxen)",
        "3. Updated clinical notes documenting ongoing symptoms despite conservative treatment",
    ]
    for item in items:
        c.drawString(50, y, item)
        y -= 12

    y -= 14
    c.setFont("Helvetica", 8)
    c.drawString(36, y, "Reviewed by: Dr. Howard P. Gaines, MD, MBA — Medical Director")
    y -= 20
    c.setFont("Helvetica-Bold", 8)
    c.drawString(36, y, "APPEAL RIGHTS: You or the member may appeal within 180 days by contacting 1-800-555-0149.")
    y -= 12
    c.setFont("Helvetica", 7)
    c.drawString(36, y, "Peer-to-peer review available M-F 8am-5pm CT. Call 1-800-555-0150 to schedule.")

    c.save()
    add_scan_artifacts(path, path, noise_level="light")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT 5: Pharmacy Refill Request
# Handwritten-style fax from pharmacy
# ═══════════════════════════════════════════════════════════════════════════

def create_pharmacy_refill_request():
    path = os.path.join(OUTPUT_DIR, "05_pharmacy_refill_request.pdf")
    c = canvas.Canvas(path, pagesize=letter)

    # Pharmacy header
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, H - 40, "CEDAR GROVE PHARMACY")
    c.setFont("Helvetica", 9)
    c.drawCentredString(W / 2, H - 54, "1580 Main Street  |  Willowdale, OR 97333")
    c.drawCentredString(W / 2, H - 66, "Phone: (555) 221-3344  |  Fax: (555) 221-3345")
    c.drawCentredString(W / 2, H - 78, "NPI: 1122334455  |  DEA: BC7654321")

    c.setStrokeColor(gray)
    c.setLineWidth(2)
    c.line(36, H - 86, W - 36, H - 86)
    c.setLineWidth(1)
    c.setStrokeColor(black)

    y = H - 106

    # Big title
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, y, "PRESCRIPTION REFILL REQUEST")
    y -= 24

    c.setFont("Courier", 8)
    c.drawString(36, y, f"Date/Time: 02/10/2026 09:17 AM")
    c.drawRightString(W - 36, y, "URGENT: Patient has 0 refills remaining")
    y -= 20

    c.line(36, y, W - 36, y)
    y -= 18

    # Form fields
    c.setFont("Helvetica-Bold", 10)
    c.drawString(36, y, "TO:")
    c.setFont("Helvetica", 10)
    c.drawString(80, y, "Dr. Evelyn Sato, DO  —  Whispering Pines Family Medicine")
    y -= 14
    c.setFont("Helvetica-Bold", 10)
    c.drawString(36, y, "FAX:")
    c.setFont("Helvetica", 10)
    c.drawString(80, y, "(555) 867-5309")

    y -= 24
    c.line(36, y, W - 36, y)
    y -= 18

    c.setFont("Helvetica-Bold", 10)
    c.drawString(36, y, "PATIENT INFORMATION")
    y -= 16
    fields = [
        ("Patient Name:", "NAKAMURA, KENJI"),
        ("Date of Birth:", "07/11/1969"),
        ("Phone:", "(555) 332-7788"),
        ("Insurance:", "Blue River Health — ID# BRH-445-9012"),
        ("Allergies on file:", "Penicillin, Sulfa"),
    ]
    for label, val in fields:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(50, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(170, y, val)
        y -= 14

    y -= 10
    c.line(36, y, W - 36, y)
    y -= 18

    c.setFont("Helvetica-Bold", 10)
    c.drawString(36, y, "MEDICATION REFILL REQUESTED")
    y -= 18

    # Medication table
    meds = [
        ("Rx #", "Medication", "Strength", "Directions", "Qty", "Last Filled"),
        ("RX-78223", "Lisinopril", "20mg", "Take 1 tab PO daily", "90", "11/12/2025"),
        ("RX-78224", "Metformin HCl", "500mg", "Take 1 tab PO BID w/meals", "180", "11/12/2025"),
        ("RX-78225", "Atorvastatin", "40mg", "Take 1 tab PO at bedtime", "90", "11/12/2025"),
    ]

    c.setFont("Helvetica-Bold", 8)
    x_positions = [50, 110, 260, 310, 440, 475]
    for i, hdr in enumerate(meds[0]):
        c.drawString(x_positions[i], y, hdr)
    y -= 4
    c.line(50, y, W - 50, y)
    y -= 13

    c.setFont("Helvetica", 8)
    for row in meds[1:]:
        for i, val in enumerate(row):
            c.drawString(x_positions[i], y, val)
        y -= 13

    y -= 16
    c.line(36, y, W - 36, y)
    y -= 18

    # Doctor response section
    c.setFont("Helvetica-Bold", 10)
    c.drawString(36, y, "PRESCRIBER RESPONSE (please check and fax back):")
    y -= 18

    options = [
        "APPROVED as requested — Refill authorized for _____ months",
        "APPROVED with changes (see below)",
        "DENIED — Patient must schedule appointment before refill",
        "DENIED — Medication discontinued / changed to: ________________",
    ]
    for opt in options:
        c.rect(50, y - 2, 10, 10, fill=False)
        c.setFont("Helvetica", 9)
        c.drawString(66, y, opt)
        y -= 16

    y -= 10
    c.setFont("Helvetica", 9)
    c.drawString(36, y, "Notes: _______________________________________________________________________________")
    y -= 20
    c.drawString(36, y, "Prescriber Signature: ______________________________  Date: ______________")

    y -= 30
    c.setFont("Helvetica", 7)
    c.drawString(36, y, "Please respond within 48 hours. Patient last seen: 10/28/2025.")
    y -= 10
    c.drawString(36, y, "If no response received, pharmacy will contact patient to schedule office visit.")

    c.save()
    return path


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT 6: Insurance Correspondence — Explanation of Benefits / Coverage
# ═══════════════════════════════════════════════════════════════════════════

def create_insurance_correspondence():
    path = os.path.join(OUTPUT_DIR, "06_insurance_correspondence.pdf")
    c = canvas.Canvas(path, pagesize=letter)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(36, H - 40, "BLUE RIVER HEALTH")
    c.setFont("Helvetica", 8)
    c.drawString(36, H - 52, "Member Services Division")
    c.drawString(36, H - 62, "2900 Insurance Parkway, Suite 500, Portland, OR 97201")
    c.drawString(36, H - 72, "Phone: 1-888-555-0222  |  Fax: 1-888-555-0223")

    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(W - 36, H - 52, "Fax Date: 02/06/2026")
    c.drawRightString(W - 36, H - 64, "Ref: BRH-COB-2026-04418")

    c.line(36, H - 80, W - 36, H - 80)

    y = H - 100
    c.setFont("Helvetica", 9)
    c.drawString(36, y, "TO: Whispering Pines Family Medicine — Billing Department")
    y -= 14
    c.drawString(36, y, "FAX: (555) 867-5310")
    y -= 20

    c.setFont("Helvetica-Bold", 11)
    c.drawString(36, y, "RE: COORDINATION OF BENEFITS — REQUEST FOR INFORMATION")
    y -= 20

    c.line(36, y, W - 36, y)
    y -= 16

    c.setFont("Helvetica", 9)
    body_lines = [
        "Dear Billing Department,",
        "",
        "Our records indicate that the following member may have other health insurance",
        "coverage. To properly coordinate benefits and process pending claims, we require",
        "the information requested below.",
        "",
        "MEMBER: NAKAMURA, KENJI (ID# BRH-445-9012, DOB 07/11/1969)",
        "",
        "PENDING CLAIMS:",
        "  Claim #BRH-CL-2026-11234  DOS: 01/15/2026  Charges: $385.00  Office Visit + Labs",
        "  Claim #BRH-CL-2026-11235  DOS: 01/15/2026  Charges: $127.00  HbA1c + Lipid Panel",
        "",
        "The above claims are currently PENDED awaiting coordination of benefits (COB)",
        "information. Our records show a possible secondary carrier.",
        "",
        "PLEASE PROVIDE OR CONFIRM THE FOLLOWING:",
        "",
        "  1. Does this patient have other health insurance coverage?  YES / NO",
        "  2. If yes, please provide:",
        "     - Carrier name: _____________________________________",
        "     - Policy/Group #: ___________________________________",
        "     - Policyholder name: ________________________________",
        "     - Effective date: ____________________________________",
        "  3. Is this practice aware of any workers' compensation or auto accident",
        "     claim related to the dates of service listed above?  YES / NO",
        "",
        "Please complete and fax this form back to 1-888-555-0223 within 30 days.",
        "If we do not receive a response, claims will be processed based on available",
        "information, which may result in reduced payment or denial.",
        "",
        "Thank you for your prompt attention to this matter.",
        "",
        "Member Services — Coordination of Benefits Unit",
        "Blue River Health",
    ]

    for line in body_lines:
        c.drawString(50, y, line)
        y -= 12

    y -= 10
    c.setFont("Helvetica", 7)
    c.drawString(36, y, "This communication contains confidential information. If you are not the intended recipient, please destroy and notify Blue River Health.")

    c.save()
    add_scan_artifacts(path, path, noise_level="light")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT 7: Patient Records Request (HIPAA)
# Formal records release request from another provider
# ═══════════════════════════════════════════════════════════════════════════

def create_records_request():
    path = os.path.join(OUTPUT_DIR, "07_patient_records_request.pdf")
    c = canvas.Canvas(path, pagesize=letter)

    # Requesting provider header
    c.setFont("Helvetica-Bold", 13)
    c.drawString(36, H - 40, "LAKESIDE ORTHOPEDIC CLINIC")
    c.setFont("Helvetica", 8)
    c.drawString(36, H - 52, "Dr. Marcus Bellingham, MD  |  Dr. Priya Venkatesh, MD")
    c.drawString(36, H - 62, "3100 Lakewood Drive, Suite 210  |  Meadowbrook, CO 80555")
    c.drawString(36, H - 72, "Phone: (555) 776-4400  |  Fax: (555) 776-4401")

    c.line(36, H - 80, W - 36, H - 80)

    y = H - 98

    c.setFont("Courier", 8)
    c.drawString(36, y, "FAX TRANSMISSION — 02/11/2026 10:44 AM — Pages: 1")
    y -= 16

    c.setFont("Helvetica", 9)
    c.drawString(36, y, "TO: Whispering Pines Family Medicine / Medical Records Dept")
    y -= 13
    c.drawString(36, y, "FAX: (555) 867-5309")
    y -= 13
    c.drawString(36, y, "FROM: Lakeside Orthopedic Clinic — Dr. Marcus Bellingham, MD")
    y -= 20

    c.line(36, y, W - 36, y)
    y -= 18

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W / 2, y, "REQUEST FOR MEDICAL RECORDS")
    y -= 16
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(W / 2, y, "Pursuant to signed patient authorization (HIPAA compliant)")
    y -= 20

    c.line(36, y, W - 36, y)
    y -= 16

    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, y, "PATIENT INFORMATION:")
    y -= 15
    fields = [
        ("Patient Name:", "DELACROIX, THOMAS R."),
        ("Date of Birth:", "09/22/1971"),
        ("SSN Last 4:", "XXXX (on file with authorization form)"),
        ("Phone:", "(555) 998-3321"),
    ]
    for label, val in fields:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(50, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(160, y, val)
        y -= 14

    y -= 8
    c.line(36, y, W - 36, y)
    y -= 16

    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, y, "RECORDS REQUESTED:")
    y -= 16

    c.setFont("Helvetica", 9)
    items = [
        ("Date Range:", "January 2024 — Present"),
        ("Record Types:", ""),
    ]
    for label, val in items:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(50, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(160, y, val)
        y -= 14

    # Checkboxes for record types
    record_types = [
        ("Office/Progress Notes", True),
        ("Lab Results", True),
        ("Imaging Reports", True),
        ("Medication List", True),
        ("Immunization Records", False),
        ("Surgical/Procedure Notes", False),
        ("Referral Correspondence", True),
        ("Complete Medical Record", False),
    ]

    col1_x, col2_x = 60, 300
    items_per_col = 4
    for i, (rt, checked) in enumerate(record_types):
        x = col1_x if i < items_per_col else col2_x
        row_y = y if i < items_per_col else y + (items_per_col * 16)
        row_y -= (i % items_per_col) * 16
        c.rect(x, row_y - 2, 10, 10, fill=False)
        if checked:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x + 1.5, row_y - 0.5, "X")
        c.setFont("Helvetica", 9)
        c.drawString(x + 16, row_y, rt)

    y -= (items_per_col * 16) + 14

    c.line(36, y, W - 36, y)
    y -= 16

    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, y, "REASON FOR REQUEST:")
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(50, y, "New patient evaluation for chronic low back pain. Patient is transferring")
    y -= 12
    c.drawString(50, y, "orthopedic care. Need to review prior treatment history and imaging to")
    y -= 12
    c.drawString(50, y, "avoid unnecessary duplicate testing.")

    y -= 20
    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, y, "AUTHORIZATION:")
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(50, y, "Signed patient authorization form is on file at our office.")
    y -= 12
    c.drawString(50, y, "A copy will be mailed upon request or can be faxed to (555) 867-5309.")

    y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(36, y, "Please fax records to: (555) 776-4401  ATTN: Medical Records / Dr. Bellingham")
    y -= 14
    c.drawString(36, y, "If questions, please call (555) 776-4400 and ask for Rebecca (Records Coordinator).")

    y -= 24
    c.setFont("Helvetica", 7)
    c.drawString(36, y, "This request is made in compliance with HIPAA Privacy Rule (45 CFR 164.524). Records should be provided within 30 days.")

    c.save()
    return path


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT 8: Marketing / Junk Fax
# EHR vendor spam — flashy, sales-y
# ═══════════════════════════════════════════════════════════════════════════

def create_junk_fax():
    path = os.path.join(OUTPUT_DIR, "08_junk_marketing_fax.pdf")
    c = canvas.Canvas(path, pagesize=letter)

    # Big flashy header
    c.setFillColor(HexColor("#003366"))
    c.rect(0, H - 100, W, 100, fill=True, stroke=False)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(W / 2, H - 45, "STILL USING PAPER CHARTS?")
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, H - 68, "Switch to MedFlow EHR Pro and Save 40%!")
    c.setFont("Helvetica", 10)
    c.drawCentredString(W / 2, H - 88, "Limited Time Offer for Practices with 1-10 Providers")

    c.setFillColor(black)
    y = H - 130

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W / 2, y, "Why 5,000+ Practices Trust MedFlow EHR Pro")
    y -= 24

    benefits = [
        ("Cloud-Based", "Access patient records from anywhere — tablet, laptop, or phone"),
        ("Built-in E-Prescribing", "EPCS-certified, integrated with SureScripts network"),
        ("Automated Coding", "AI-powered ICD-10 and CPT code suggestions save hours daily"),
        ("Free Data Migration", "We handle the transfer from your current system at no charge"),
        ("24/7 Live Support", "US-based support team available around the clock"),
        ("MIPS/MACRA Ready", "Built-in quality reporting for Medicare incentive programs"),
    ]

    c.setFont("Helvetica", 10)
    for title, desc in benefits:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(72, y, f">> {title}")
        c.setFont("Helvetica", 9)
        c.drawString(90, y - 13, desc)
        y -= 30

    y -= 10
    # "Special offer" box
    c.setStrokeColor(HexColor("#CC0000"))
    c.setLineWidth(2)
    c.rect(60, y - 70, W - 120, 70, fill=False)
    c.setLineWidth(1)

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(HexColor("#CC0000"))
    c.drawCentredString(W / 2, y - 18, "EXCLUSIVE FAX OFFER — SAVE $4,200/YEAR")
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    c.drawCentredString(W / 2, y - 36, "Sign up by March 15, 2026 and get your first 3 months FREE")
    c.drawCentredString(W / 2, y - 50, "Plus FREE on-site training for your entire staff ($2,500 value)")

    y -= 95

    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(W / 2, y, "Call NOW: 1-800-555-MFLO (6356)")
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawCentredString(W / 2, y, "Or visit www.medflowehr.example.com/fax-offer")
    y -= 16
    c.drawCentredString(W / 2, y, "Or reply to this fax with your contact info:")

    y -= 24
    c.setFont("Helvetica", 9)
    fields = [
        "Practice Name: _______________________________________________",
        "Contact Person: ______________________________________________",
        "Phone: ____________________  Email: __________________________",
        "# of Providers: _____  Current EHR (if any): ___________________",
    ]
    for f in fields:
        c.drawString(72, y, f)
        y -= 16

    y -= 16
    c.setFont("Helvetica", 7)
    c.drawCentredString(W / 2, y, "MedFlow Solutions Inc. | 9500 Commerce Blvd, Suite 100 | Dallas, TX 75201")
    y -= 10
    c.drawCentredString(W / 2, y, "To be removed from our fax list, call 1-800-555-6357 or fax 'REMOVE' to 1-800-555-6358")
    y -= 10
    c.drawCentredString(W / 2, y, "This advertisement complies with the Telephone Consumer Protection Act (TCPA). Unsolicited fax ID: MF-2026-FAX-00441")

    c.save()
    add_scan_artifacts(path, path, noise_level="heavy")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# MAIN — Generate all documents
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Generating synthetic healthcare fax documents...\n")

    generators = [
        ("01 - Lab Result (CBC Panel)", create_lab_result),
        ("02 - Referral Response (Cardiology)", create_referral_response),
        ("03 - Prior Auth APPROVED (MRI)", create_prior_auth_approved),
        ("04 - Prior Auth DENIED (Injection)", create_prior_auth_denied),
        ("05 - Pharmacy Refill Request", create_pharmacy_refill_request),
        ("06 - Insurance Correspondence (COB)", create_insurance_correspondence),
        ("07 - Patient Records Request", create_records_request),
        ("08 - Marketing/Junk Fax (EHR Vendor)", create_junk_fax),
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
    print(f"Generated {len(created_files)} of {len(generators)} documents in {OUTPUT_DIR}/")
    print(f"{'='*60}")
