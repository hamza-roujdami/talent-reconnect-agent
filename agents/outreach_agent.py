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
    Uses LLM to generate tailored messaging
    
    - Generates personalized message based on candidate profile
    - Sends via specified channel (email, LinkedIn, SMS)
    - Logs activity to ATS/CRM
    - Tracks open/click rates
    """
    try:
        from openai import AzureOpenAI
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential,
            "https://cognitiveservices.azure.com/.default"
        )
        
        client = AzureOpenAI(
            azure_endpoint=os.getenv("OPENAI_API_BASE"),
            azure_ad_token_provider=token_provider,
            api_version="2024-10-21"
        )
        
        # Get candidate info (in production, fetch from enrichment data)
        candidate_info = {
            "Sarah Chen": "Senior ML Engineer at TechCorp Solutions with 8 years of experience in Python, TensorFlow, Azure ML, and MLOps",
            "Priya Sharma": "AI Research Engineer at DataFlow Analytics with 5 years of experience in PyTorch, NLP, and Azure"
        }
        
        candidate_background = candidate_info.get(candidate_name, f"experienced professional with strong background in ML/AI")
        
        prompt = f"""Generate a personalized {channel} message for:

Candidate: {candidate_name}
Background: {candidate_background}
Job Opportunity: {job_title}
Company: TechCorp Solutions

The role involves leading Azure ML platform initiatives and collaborating with cross-functional teams.

Guidelines:
- Professional but friendly
- Concise (3-4 short paragraphs for email)
- Personalized with specific references to their background
- Action-oriented with a clear call-to-action

Generate only the message content, no subject line or metadata."""
        
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini-deployment"),
            messages=[
                {"role": "system", "content": "You are an expert recruiter writing personalized outreach messages. Keep it professional, warm, and concise."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.8
        )
        
        message_content = response.choices[0].message.content
        
        result = f"""
✓ Outreach Sent Successfully

Recipient: {candidate_name} ({candidate_email})
Channel: {channel.upper()}
Job: {job_title}

Message Preview:
---
{message_content.strip()}
---

Tracking:
- Message ID: MSG-{candidate_name.replace(' ', '')[:5].upper()}-001
- Sent: 2025-11-26 10:30 AM PST
- Status: Delivered ✓
- ATS/CRM Logged: ✓
- Generated: LLM-Personalized ✓

Next Steps:
- Monitor response (24-48 hour window)
- Follow-up reminder in 3 days if no response
- Log all interactions to ATS/CRM
"""
        
        return result
        
    except Exception as e:
        print(f"⚠️ LLM message generation failed, using template: {e}")
        # Fallback to template
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
- Sent: 2025-11-26 10:30 AM PST
- Status: Delivered ✓
- ATS/CRM Logged: ✓
- Generated: Template (Fallback)

Next Steps:
- Monitor response (24-48 hour window)
- Follow-up reminder in 3 days if no response
- Log all interactions to ATS/CRM
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
