"""
Email Tool - Outreach Email Generation

Generates and sends personalized outreach emails.
"""

from typing import Annotated, List
from pydantic import Field


# Candidate email mapping (from mock data)
CANDIDATE_EMAILS = {
    "Sarah Chen": "sarah.chen@email.com",
    "Ahmed Al-Hassan": "ahmed.alhassan@email.com",
    "Priya Sharma": "priya.sharma@email.com",
    "Marcus Johnson": "marcus.j@email.com",
    "Fatima Al-Zahra": "fatima.alzahra@email.com",
    "James Williams": "james.w@email.com",
    "Noura Al-Rashid": "noura.alrashid@email.com",
}


def send_outreach_emails(
    candidate_names: Annotated[List[str], Field(description="List of candidate names to send emails to")],
    job_title: Annotated[str, Field(description="The job title for the outreach")],
    company_name: Annotated[str, Field(description="The hiring company name")] = "G42"
) -> str:
    """
    Generate and send personalized outreach emails to selected candidates.
    Returns confirmation with email previews.
    """
    
    result = f"""
## 📧 Outreach Emails Sent Successfully!

**Job Position:** {job_title}  
**Company:** {company_name}  
**Candidates Contacted:** {len(candidate_names)}

---
"""
    
    for i, name in enumerate(candidate_names, 1):
        email = CANDIDATE_EMAILS.get(name, f"{name.lower().replace(' ', '.')}@email.com")
        first_name = name.split()[0]
        
        result += f"""
### ✉️ Email {i}: {name}
**To:** {email}  
**Subject:** Exciting {job_title} Opportunity at {company_name}

---

Hi {first_name},

I hope this message finds you well! I came across your profile and was impressed by your background in AI/ML engineering.

We have an exciting opportunity for a **{job_title}** position at **{company_name}** that I think could be a great fit for your experience and career goals.

**Why this role might interest you:**
- Work on cutting-edge AI/ML projects at scale
- Collaborate with world-class engineers and researchers
- Competitive compensation and benefits package
- Be part of the UAE's leading AI company

Would you be open to a brief conversation this week to discuss further? I'd love to share more details about the role and learn about your career aspirations.

Looking forward to hearing from you!

Best regards,  
**Talent Acquisition Team**  
{company_name}

---
**Tracking ID:** MSG-{name.replace(' ', '')[:5].upper()}-{i:03d}  
**Status:** ✅ Delivered  
**Next Action:** Follow-up in 3 days if no response

---
"""
    
    result += f"""
## 📊 Outreach Summary

| Metric | Value |
|--------|-------|
| Emails Sent | {len(candidate_names)} |
| Delivery Status | ✅ All Delivered |
| Expected Response Rate | ~40% |
| Follow-up Scheduled | 3 days |

All activities have been logged to the ATS/CRM system.

**What's next?**
- Monitor responses over the next 24-48 hours
- I'll notify you when candidates respond
- Follow-up emails will be sent automatically after 3 days if no response
"""
    
    return result
