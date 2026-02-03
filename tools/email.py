"""Mock email tool for demo purposes.

Simulates sending outreach emails to candidates.
In production, this would integrate with an email service (SendGrid, etc.).
"""

import json
from datetime import datetime


def send_outreach_email(
    candidate_name: str,
    candidate_email: str = None,
    subject: str = None,
    body: str = None,
) -> str:
    """Simulate sending an outreach email to a candidate.
    
    Args:
        candidate_name: Name of the candidate
        candidate_email: Email address (optional, will be mocked)
        subject: Email subject line
        body: Email body content
        
    Returns:
        JSON string with confirmation details
    """
    # Generate mock email if not provided
    if not candidate_email:
        # Create a plausible email from name
        name_parts = candidate_name.lower().split()
        if len(name_parts) >= 2:
            candidate_email = f"{name_parts[0]}.{name_parts[-1]}@email.com"
        else:
            candidate_email = f"{name_parts[0]}@email.com"
    
    # Default subject if not provided
    if not subject:
        subject = "Exciting Opportunity - Let's Connect!"
    
    # Log the "sent" email (in production, actually send it)
    timestamp = datetime.now().isoformat()
    
    result = {
        "status": "sent",
        "message_id": f"msg_{hash(candidate_name + timestamp) % 100000:05d}",
        "recipient": {
            "name": candidate_name,
            "email": candidate_email,
        },
        "subject": subject,
        "sent_at": timestamp,
        "note": "Email queued for delivery. Candidate should receive it within 5 minutes.",
    }
    
    # Print for demo visibility
    print(f"\n📧 EMAIL SENT")
    print(f"   To: {candidate_name} <{candidate_email}>")
    print(f"   Subject: {subject}")
    print(f"   Status: ✓ Delivered\n")
    
    return json.dumps(result, indent=2)
