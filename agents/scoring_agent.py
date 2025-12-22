"""
Scoring Agent - Ranks candidates with feedback history integration.

This agent:
1. Takes search results from SearchAgent
2. Fetches interview feedback history for each candidate
3. Applies bonus/penalty based on past performance
4. Surfaces red flags from previous interviews
5. Returns re-ranked candidates with context

Feedback is stored in Azure AI Search 'feedback' index.
"""
from agent_framework import ChatAgent
from tools.feedback import (
    get_feedback_history,
    get_feedback_by_candidate_id,
    format_feedback_summary,
    add_feedback,
)


def fetch_candidate_feedback(candidate_emails: list[str]) -> str:
    """Fetch interview feedback history for candidates by email.
    
    Args:
        candidate_emails: List of candidate email addresses to look up
        
    Returns:
        Formatted feedback summary for each candidate with history
    """
    results = []
    candidates_with_history = 0
    red_flags = 0
    
    for email in candidate_emails:
        feedback = get_feedback_history(email)
        if feedback:
            candidates_with_history += 1
            if feedback.get("has_red_flag"):
                red_flags += 1
            results.append(f"**{email}**\n{format_feedback_summary(feedback)}")
    
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


def fetch_feedback_by_ids(candidate_ids: list[str]) -> str:
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
    
    for cid in candidate_ids:
        feedback = get_feedback_by_candidate_id(cid)
        if feedback:
            candidates_with_history += 1
            name = feedback.get("candidate_name", cid)
            if feedback.get("has_red_flag"):
                red_flags += 1
            results.append(f"**{name}** ({cid})\n{format_feedback_summary(feedback)}")
    
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


def record_interview_feedback(
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
    
    feedback = add_feedback(
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
    
    return f"✅ Feedback recorded for {candidate_name} ({candidate_email})\n" + format_feedback_summary(
        get_feedback_history(candidate_email)
    )


def create_scoring_agent(chat_client) -> ChatAgent:
    """Create the Scoring Agent with feedback history tools.
    
    This agent:
    1. Fetches interview feedback for candidates from Azure AI Search
    2. Highlights candidates with positive history (bonus)
    3. Flags candidates with previous no-hire recommendations
    4. Can record new interview feedback
    """
    return chat_client.create_agent(
        name="scoring_agent",
        instructions="""You are a recruiting scoring specialist with access to interview feedback history stored in Azure AI Search.

## Your Tools

1. **fetch_candidate_feedback** - Get interview history by email
   - Pass a list of candidate email addresses
   - Returns past interview scores, recommendations, strengths, concerns

2. **fetch_feedback_by_ids** - Get interview history by candidate ID
   - Use when you have candidate_id from search results
   - More reliable linking to the resumes index

3. **record_interview_feedback** - Save new interview feedback
   - Use after an interview is completed
   - Requires: candidate_id, email, name, interviewer, role, etc.
   - Stored in Azure AI Search 'feedback' index

## When Called

You are called after SearchAgent returns candidates. Your job is to:

1. **Fetch feedback** for all returned candidates
   - Try fetch_feedback_by_ids first if you have candidate IDs
   - Fall back to fetch_candidate_feedback with emails
2. **Highlight** candidates with positive history:
   - "Strong hire" → +15 points, mention past success
   - "Hire" → +5 points
3. **Flag concerns** for candidates with negative history:
   - "No hire" → -15 points, surface the concern
   - Show this as a ⚠️ red flag
4. **Re-rank** candidates based on adjusted scores
5. **Summarize** the feedback findings

## Output Format

After fetching feedback, present:

```
📊 **Candidates Re-ranked with Interview History**

1. **Pradeep Al-Zaabi** (92% → adjusted from 77%)
   ✅ Previous: Strong hire for Senior AI Engineer
   💪 Past strengths: "Strong PyTorch expertise, excellent system design"
   
2. **Faisal Khan** (82% → adjusted from 77%)
   ✅ Previous: Hire for ML Engineer
   💪 Past strengths: "Deep Kubernetes knowledge"
   ⚠️ Note: "Limited experience with real-time ML systems"

3. **Robert Chowdhury** (58% → adjusted from 73%)
   ⚠️ **Red Flag:** Previous no-hire recommendation
   Previous concern: "Communication could be clearer"
   Note: More recent interview showed improvement
```

## Guidelines

- Always fetch feedback before re-ranking
- Be transparent about adjustments
- Red flags should be visible but not automatic disqualifiers
- Recent interviews matter more than old ones
""",
        tools=[fetch_candidate_feedback, record_interview_feedback],
    )
