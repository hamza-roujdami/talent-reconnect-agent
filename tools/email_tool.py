"""Email tool - definition and implementation.

Simulates sending outreach emails to candidates.
In production, integrate with an email service (SendGrid, Graph API, etc.).
"""

import json
from datetime import datetime

from azure.ai.projects.models import FunctionTool


# =============================================================================
# Tool Definition (for Foundry agent)
# =============================================================================

SEND_EMAIL_TOOL = FunctionTool(
    name="send_outreach_email",
    description="Send a personalized outreach email to a candidate.",
    parameters={
        "type": "object",
        "properties": {
            "candidate_name": {
                "type": "string",
                "description": "Full name of the candidate"
            },
            "candidate_email": {
                "type": "string",
                "description": "Email address (optional)"
            },
            "subject": {
                "type": "string",
                "description": "Email subject line"
            },
            "body": {
                "type": "string",
                "description": "Email body content"
            },
        },
        "required": ["candidate_name", "subject", "body"],
    },
)


# =============================================================================
# Tool Implementation
# =============================================================================

def send_outreach_email(
    candidate_name: str,
    candidate_email: str = None,
    subject: str = None,
    body: str = None,
) -> str:
    """Simulate sending an outreach email to a candidate."""
    # Generate mock email if not provided
    if not candidate_email:
        name_parts = candidate_name.lower().split()
        if len(name_parts) >= 2:
            candidate_email = f"{name_parts[0]}.{name_parts[-1]}@email.com"
        else:
            candidate_email = f"{name_parts[0]}@email.com"
    
    if not subject:
        subject = "Exciting Opportunity - Let's Connect!"
    
    timestamp = datetime.now().isoformat()
    
    result = {
        "status": "sent",
        "message_id": f"msg_{hash(candidate_name + timestamp) % 100000:05d}",
        "recipient": {"name": candidate_name, "email": candidate_email},
        "subject": subject,
        "sent_at": timestamp,
    }
    
    print(f"\n📧 EMAIL SENT to {candidate_name} <{candidate_email}>\n")
    
    return json.dumps(result, indent=2)
