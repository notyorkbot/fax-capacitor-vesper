# Synthetic Fax Test Corpus

This directory will contain synthetic fax PDFs for testing the classification pipeline.

**All documents in this directory use fictional patient data.** No real PHI is stored here.

## Expected Files (to be created in Phase 1)

| File | Document Type | Notes |
|------|--------------|-------|
| `lab_result_blood_work.pdf` | Lab Result | Clean scan, typed, critical value flagged |
| `lab_result_imaging.pdf` | Lab Result | Imaging report, multi-page |
| `referral_response.pdf` | Referral Response | Specialist consult note |
| `prior_auth_denial.pdf` | Prior Auth Decision | Denial with appeal deadline |
| `prior_auth_approval.pdf` | Prior Auth Decision | Approval with auth number |
| `pharmacy_refill.pdf` | Pharmacy Request | Refill request from pharmacy |
| `insurance_eob.pdf` | Insurance Correspondence | EOB with claim details |
| `records_request.pdf` | Records Request | Records request from another provider |
| `marketing_junk.pdf` | Marketing / Junk | Equipment vendor solicitation |

## Quality Variations

Some documents should intentionally include:
- Slightly angled/rotated scans
- Faded text or low contrast
- Handwritten annotations over typed text
- Fax header artifacts (date/time stamps, page numbers)
- Cover sheets preceding the actual content
