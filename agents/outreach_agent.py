"""
ConnectPilot (Outreach Agent) - Drafts and confirms personalized recruitment emails.

Has access to:
- send_outreach_email: Draft and prepare emails for candidates
- confirm_outreach_delivery: Mark the email as sent (simulated)
"""
from typing import Optional

from agent_framework import ChatAgent
from tools.outreach_email import send_outreach_email, confirm_outreach_delivery

OUTREACH_AGENT_NAME = "ConnectPilot"


def create_outreach_agent(
    chat_client,
    *,
    middleware: Optional[list] = None,
    function_middleware: Optional[list] = None,
) -> ChatAgent:
    """Create the Outreach Agent for candidate communication.
    
    This agent:
    1. Takes selected candidates from user
    2. Drafts personalized recruitment emails
    3. Incorporates candidate background and job context
    
    Args:
        chat_client: The chat client to use
        middleware: Agent-level middleware for logging/monitoring
        function_middleware: Function-level middleware for tool calls
    """
    # Combine middleware lists for new API
    all_middleware = []
    if middleware:
        all_middleware.extend(middleware)
    if function_middleware:
        all_middleware.extend(function_middleware)
    
    return chat_client.as_agent(
        name=OUTREACH_AGENT_NAME,
        default_options={"temperature": 0.2},
        middleware=all_middleware or None,
        tools=[send_outreach_email, confirm_outreach_delivery],
        instructions="""You draft recruitment emails.

## Tools
1. **send_outreach_email(candidate_name, candidate_email, job_title, personalization, company_name)**
   - Use whenever the user asks you to draft or update a message.
2. **confirm_outreach_delivery(candidate_name, candidate_email, job_title, company_name)**
   - Call immediately after the user explicitly approves sending the email.

## CRITICAL RULES
1. Requests like "email candidate 1" or "reach out to Noor" must call send_outreach_email using the candidate data from search/insight results.
2. Extract full names from earlier results (e.g., "Zayed Khan") and infer email formats if necessary.
3. After the user says "send", "looks good", "proceed", or similar approval, call confirm_outreach_delivery using the same candidate details to acknowledge the (simulated) send.
4. Never claim an email was sent unless confirm_outreach_delivery was called.

## Example
User: "email candidate 1"
→ Call: send_outreach_email(
    candidate_name="Zayed Khan",
    candidate_email="zayed.khan@infosys.com",
    job_title="Data Engineer",
    personalization="Your 8 years of experience with Python and GCP..."
)

User: "Great, send it"
→ Call: confirm_outreach_delivery(
    candidate_name="Zayed Khan",
    candidate_email="zayed.khan@infosys.com",
    job_title="Data Engineer"
)
""",
    )
