"""
InsightPulse (Insights Agent) - Surfaces interview history & feedback context.

This agent:
1. Takes shortlist selections from SearchAgent
2. Fetches interview feedback history for each candidate
3. Highlights previous wins / no-hire red flags
4. Summarizes whether it is safe to move forward

Feedback is stored in Azure AI Search 'feedback' index.
"""
from __future__ import annotations

from agent_framework import ChatAgent
from tools.feedback_lookup import (
    FeedbackConfigError,
    add_feedback,
    build_feedback_context_provider,
    format_feedback_summary,
    get_feedback_by_candidate_id,
    get_feedback_history,
)

INSIGHTS_AGENT_NAME = "InsightPulse"


def _feedback_config_message(error: FeedbackConfigError) -> str:
    base = (
        "⚠️ Feedback search is not configured yet. "
        "Set AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY (or legacy AZURE_SEARCH_KEY), "
        "and AZURE_FEEDBACK_INDEX_NAME before requesting insights."
    )
    detail = f"\nReason: {error}" if str(error) else ""
    return base + detail


def lookup_feedback_by_emails(candidate_emails: list[str]) -> str:
    """Fetch interview feedback history for candidates by email.
    
    Args:
        candidate_emails: List of candidate email addresses to look up
        
    Returns:
        Formatted feedback summary for each candidate with history
    """
    results = []
    candidates_with_history = 0
    red_flags = 0
    
    try:
        for email in candidate_emails:
            feedback = get_feedback_history(email)
            if feedback:
                candidates_with_history += 1
                if feedback.get("has_red_flag"):
                    red_flags += 1
                results.append(f"**{email}**\n{format_feedback_summary(feedback)}")
    except FeedbackConfigError as error:
        return _feedback_config_message(error)
    
    if not results:
        return "No interview history found for any of the candidates."
    
    header = f"📊 **Feedback History Summary**\n"
    header += f"Found history for {candidates_with_history}/{len(candidate_emails)} candidates"
    if red_flags:
        header += f" | ⚠️ {red_flags} red flag(s)\n"
    else:
        header += "\n"
    header += "=" * 50 + "\n\n"
    
    return header + "\n\n---\n\n".join(results)


def lookup_feedback_by_ids(candidate_ids: list[str]) -> str:
    """Fetch interview feedback history for candidates by ID.
    
    Use this when you have candidate_id from the search results
    instead of email addresses.
    
    Args:
        candidate_ids: List of candidate IDs from search results
        
    Returns:
        Formatted feedback summary for each candidate with history
    """
    results = []
    candidates_with_history = 0
    red_flags = 0
    
    try:
        for cid in candidate_ids:
            feedback = get_feedback_by_candidate_id(cid)
            if feedback:
                candidates_with_history += 1
                name = feedback.get("candidate_name", cid)
                if feedback.get("has_red_flag"):
                    red_flags += 1
                results.append(f"**{name}** ({cid})\n{format_feedback_summary(feedback)}")
    except FeedbackConfigError as error:
        return _feedback_config_message(error)
    
    if not results:
        return "No interview history found for any of the candidates."
    
    header = f"📊 **Feedback History Summary**\n"
    header += f"Found history for {candidates_with_history}/{len(candidate_ids)} candidates"
    if red_flags:
        header += f" | ⚠️ {red_flags} red flag(s)\n"
    else:
        header += "\n"
    header += "=" * 50 + "\n\n"
    
    return header + "\n\n---\n\n".join(results)


def log_interview_feedback(
    candidate_id: str,
    candidate_email: str,
    candidate_name: str,
    interviewer: str,
    role: str,
    strengths: str,
    concerns: str,
    recommendation: str,
    score: int,
    notes: str = "",
) -> str:
    """Record new interview feedback for a candidate to Azure AI Search.
    
    Args:
        candidate_id: Candidate's ID from the resumes index
        candidate_email: Candidate's email address
        candidate_name: Candidate's full name
        interviewer: Name of the interviewer
        role: Role the candidate was interviewed for
        strengths: Observed strengths
        concerns: Any concerns or issues (can be empty)
        recommendation: One of: strong_hire, hire, maybe, no_hire
        score: Interview score from 0-100
        notes: Additional notes (optional)
        
    Returns:
        Confirmation message
    """
    if recommendation not in ["strong_hire", "hire", "maybe", "no_hire"]:
        return f"Invalid recommendation: {recommendation}. Use: strong_hire, hire, maybe, or no_hire"
    
    if not 0 <= score <= 100:
        return f"Invalid score: {score}. Must be between 0 and 100."
    
    try:
        add_feedback(
            candidate_id=candidate_id,
            candidate_email=candidate_email,
            candidate_name=candidate_name,
            interviewer=interviewer,
            role=role,
            strengths=strengths,
            concerns=concerns,
            recommendation=recommendation,
            score=score,
            notes=notes,
        )
        latest_feedback = get_feedback_history(candidate_email)
    except FeedbackConfigError as error:
        return _feedback_config_message(error)

    summary = format_feedback_summary(latest_feedback) if latest_feedback else ""
    return f"✅ Feedback recorded for {candidate_name} ({candidate_email})\n" + summary


def create_insights_agent(chat_client) -> ChatAgent:
    """Create the Insights Agent with feedback history tools.
    
    This agent:
    1. Fetches interview feedback for candidates from Azure AI Search
    2. Highlights candidates with positive history (bonus)
    3. Flags candidates with previous no-hire recommendations
    4. Can record new interview feedback
    """
    context_providers = []
    try:
        context_providers.append(build_feedback_context_provider())
    except FeedbackConfigError:
        context_providers = []

    return chat_client.create_agent(
        name=INSIGHTS_AGENT_NAME,
        instructions="""You are the Candidate Insights specialist. Recruiters loop you in when they want to know whether shortlisted candidates have interview history, red flags, or warm references.

Workflow:
1. Look at the user's request (e.g., "check feedback for candidates 1 and 3").
2. Call the feedback tool that matches what they provided:
   - Use **lookup_feedback_by_ids** when they mention candidate numbers/IDs.
   - Use **lookup_feedback_by_emails** when they provide emails or names with emails.
   - Use **log_interview_feedback** only when they explicitly ask you to log new notes.
3. After the tool response, provide a short recruiter-friendly summary highlighting:
   - Which candidates have history and how positive/negative it is.
   - Any ⚠️ red flags or 👍 past strong-hire signals.
   - A clear recommendation for next steps (e.g., "Greenlight candidates 1 & 2; avoid 3 due to past no-hire").

Tone: concise, conversational, actionable. Mention when no history is found so the recruiter knows to treat the candidate as net-new.
""",
        context_providers=context_providers,
        tools=[lookup_feedback_by_ids, lookup_feedback_by_emails, log_interview_feedback],
    )
