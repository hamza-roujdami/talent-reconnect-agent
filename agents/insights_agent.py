"""
InsightPulse (Insights Agent) - Surfaces interview history & feedback context.

This agent:
1. Takes shortlist selections from SearchAgent
2. Fetches interview feedback history for each candidate
3. Highlights previous wins / no-hire red flags
4. Summarizes whether it is safe to move forward

Uses tool-based approach for reliable Azure AI Search queries in workflows.
"""
from __future__ import annotations

from agent_framework import ChatAgent
from tools.feedback_lookup import (
    FeedbackConfigError,
    add_feedback,
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
    # Debug log to help trace mapping issues
    try:
        print(f"[insights] lookup_feedback_by_emails: {candidate_emails}")
    except Exception:
        pass

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

    # Debug log to help trace mapping issues between search results and feedback index
    try:
        print(f"[insights] lookup_feedback_by_ids: {candidate_ids}")
    except Exception:
        pass
    
    try:
        for cid in candidate_ids:
            feedback = get_feedback_by_candidate_id(cid)
            # Fallback: if the "id" is actually an email, try email lookup
            if not feedback and "@" in cid:
                feedback = get_feedback_history(cid)

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


def create_insights_agent(
    chat_client,
    *,
    middleware: list | None = None,
    function_middleware: list | None = None,
) -> ChatAgent:
    """Create the Insights Agent with feedback history tools.
    
    This agent uses tool-based approach (same as TalentScout) because
    context providers don't receive full conversation context in handoff workflows.
    
    Tools:
    - lookup_feedback_by_emails: Fetch feedback by candidate emails
    - lookup_feedback_by_ids: Fetch feedback by candidate IDs
    - log_interview_feedback: Record new interview feedback
    
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
        name=INSIGHTS_AGENT_NAME,
        middleware=all_middleware or None,
        tools=[lookup_feedback_by_emails, lookup_feedback_by_ids, log_interview_feedback],
        instructions="""You are InsightPulse, the Candidate Insights specialist.

IMPORTANT: You MUST call one of your tools to get feedback. Do NOT make up feedback data.

WORKFLOW:
1. Look at the conversation for candidate emails or IDs
2. Call the appropriate tool:
   - lookup_feedback_by_emails: Use when you have emails (most common)
   - lookup_feedback_by_ids: Use when you have candidate IDs like "gen-001234"
   - log_interview_feedback: Only when user asks to record new feedback
3. Present the results clearly

OUTPUT FORMAT:
After getting tool results, summarize:
- 👍 Candidates with positive history (hire/strong_hire recommendations)
- ⚠️ Red flags (no_hire recommendations or concerns)
- 📝 Candidates with no prior history (treat as new)

End with: "Ready for outreach? Say 'email candidate 1' to draft a message."

RULES:
- ALWAYS call a tool - never skip or make up data
- Extract emails from the conversation context (look for @gmail.com, @outlook.com, etc.)
- Real candidate IDs look like "gen-XXXXXX"
""",
    )
