"""
Email tools for ConnectPilot agent.

Generates personalized recruiting outreach emails.

NOTE: This is for demo purposes only. No actual emails are sent.
In production, integrate with an email service (SendGrid, AWS SES, etc.).
"""

from datetime import datetime, timezone


def send_outreach_email(
    candidate_name: str,
    candidate_email: str,
    job_title: str,
    personalization: str = "",
    company_name: str = "our client",
) -> str:
    """
    Draft a personalized outreach email to a candidate.
    
    Args:
        candidate_name: Full name of the candidate
        candidate_email: Email address of the candidate
        job_title: The job title being offered
        personalization: Personalized message based on candidate's background
        company_name: The hiring company name
    
    Returns:
        Email preview for approval
    """
    first_name = candidate_name.split()[0] if candidate_name else "there"
    
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


def confirm_outreach_delivery(
    candidate_name: str,
    candidate_email: str,
    job_title: str,
    company_name: str = "our client",
) -> str:
    """
    Acknowledge that the drafted outreach email was (simulated) sent.
    
    Args:
        candidate_name: Full name of the candidate
        candidate_email: Email address of the candidate
        job_title: The job title being offered
        company_name: The hiring company name
        
    Returns:
        Confirmation message
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        "## ✅ Email Sent (Simulated)\n\n"
        f"**Candidate:** {candidate_name} ({candidate_email})\n"
        f"**Role:** {job_title} @ {company_name}\n"
        f"**Dispatched:** {timestamp}\n\n"
        "The outreach email has been queued for delivery in this demo environment. "
        "Let me know if you want to follow up with another candidate or edit the copy."
    )
