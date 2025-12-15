"""
Email Tool - Outreach Email Generation

Generates personalized recruiting outreach emails.
"""

from typing import Annotated, List
from pydantic import Field


def send_outreach_email(
    candidate_name: Annotated[str, Field(description="Full name of the candidate")],
    candidate_email: Annotated[str, Field(description="Email address of the candidate")],
    job_title: Annotated[str, Field(description="The job title being offered")],
    personalization: Annotated[str, Field(description="Personalized message based on candidate's background")] = "",
    company_name: Annotated[str, Field(description="The hiring company name")] = "G42",
) -> str:
    """
    Draft a personalized outreach email to a candidate.
    Returns the email preview for approval.
    """
    
    first_name = candidate_name.split()[0]
    
    email_body = f"""
## 📧 Email Draft

**To:** {candidate_email}  
**Subject:** Exciting {job_title} Opportunity at {company_name}

---

Hi {first_name},

I came across your profile and was impressed by your background. {personalization}

We're currently looking for a **{job_title}** to join our team at {company_name}. Based on your experience, I believe you could be a great fit for this role.

**What we offer:**
- Competitive compensation package
- Cutting-edge technology stack
- Collaborative team environment
- Career growth opportunities

Would you be open to a brief call to discuss this opportunity?

Best regards,  
Talent Acquisition Team  
{company_name}

---

**Status:** ✅ Draft ready for review

Would you like me to:
1. Send this email
2. Edit the message
3. Draft email for another candidate
"""
    
    return email_body
