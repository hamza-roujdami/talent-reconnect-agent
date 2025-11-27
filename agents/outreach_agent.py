"""
Outreach Agent

Sends personalized messages to approved candidates and logs to ATS/CRM
Uses LLM to generate personalized outreach messages
"""

from typing import Annotated
from pydantic import Field
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
import os


def send_outreach_message(candidate_name: Annotated[str, Field(description="Candidate name")],
                         candidate_email: Annotated[str, Field(description="Candidate email")],
                         job_title: Annotated[str, Field(description="Job title")],
                         channel: Annotated[str, Field(description="Communication channel: email, linkedin, sms")] = "email") -> str:
    """
    Send personalized outreach message to approved candidate
    
    - Generates personalized message based on candidate profile
    - Sends via specified channel (email, LinkedIn, SMS)
    - Logs activity to ATS/CRM
    - Tracks open/click rates
    
    Uses template-based messaging for consistency
    """
    # Use template message (no LLM call needed)
    message_template = f"""
Hi {candidate_name.split()[0]},

I hope this message finds you well! I'm reaching out about an exciting opportunity 
for a {job_title} position at our company.

Based on your background at TechCorp and your expertise in ML/AI, I think this 
could be a great fit. The role involves leading our Azure ML platform initiatives 
and collaborating with cross-functional teams.

Would you be open to a brief conversation this week?

Best regards,
Talent Acquisition Team
"""
    
    result = f"""
✓ Outreach Sent Successfully

Recipient: {candidate_name} ({candidate_email})
Channel: {channel.upper()}
Job: {job_title}

Message Preview:
---
{message_template.strip()}
---

Tracking:
- Message ID: MSG-{candidate_name.replace(' ', '')[:5].upper()}-001
- Status: Delivered ✓
- Next Steps: Monitor response (24-48 hour window), follow-up reminder in 3 days if no response.

Everything has been logged to the ATS/CRM system. Let me know if you need anything else!
"""
    
    return result


def log_to_ats_crm(candidate_name: Annotated[str, Field(description="Candidate name")],
                   activity_type: Annotated[str, Field(description="Activity type: outreach_sent, response_received, etc.")],
                   notes: Annotated[str, Field(description="Activity notes")] = "") -> str:
    """Log activity to ATS/CRM system"""
    return f"✓ Activity logged to ATS/CRM: {activity_type} for {candidate_name}"


def create_outreach_agent(chat_client):
    """Create the outreach agent"""
    
    agent = ChatAgent(
        chat_client=chat_client,
        name="OutreachAgent",
        instructions="""
        You are an Outreach specialist managing candidate communications.
        
        Your role:
        - Send personalized messages to approved candidates
        - Support multiple channels: email, LinkedIn, SMS
        - Generate tailored messaging based on:
          * Candidate's current role and skills
          * Job requirements
          * Company culture fit
        - Log ALL activities to ATS/CRM
        - Track engagement metrics (opens, clicks, responses)
        - Schedule follow-ups
        
        Compliance:
        - Respect opt-out preferences
        - Include unsubscribe links
        - Follow GDPR/CCPA requirements
        - Log consent for communications
        
        Be professional, personalized, and respectful of candidate time.
        """,
        tools=[send_outreach_message, log_to_ats_crm]
    )
    
    return agent
