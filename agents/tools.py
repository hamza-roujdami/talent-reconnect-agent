"""FunctionTool definitions for agents.

These are used when USE_BUILTIN_SEARCH=false (fallback mode).
The agent calls these tools, and we execute them locally with API key auth.
"""

from azure.ai.projects.models import FunctionTool


SEARCH_CANDIDATES_TOOL = FunctionTool(
    name="search_candidates",
    description="Search for candidates in the resume database. Returns matching candidates with their skills, experience, and contact info.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query - job title, skills, or keywords (e.g., 'senior Python developer Azure')"
            },
            "location": {
                "type": "string",
                "description": "Optional location filter (e.g., 'Dubai', 'Remote')"
            },
            "min_experience": {
                "type": "integer",
                "description": "Minimum years of experience"
            },
        },
        "required": ["query"],
    },
)


LOOKUP_FEEDBACK_TOOL = FunctionTool(
    name="lookup_feedback",
    description="Look up interview feedback for a candidate. Returns interview scores, notes, and recommendations.",
    parameters={
        "type": "object",
        "properties": {
            "candidate_name": {
                "type": "string",
                "description": "Name of the candidate to look up"
            },
            "candidate_id": {
                "type": "string",
                "description": "ID of the candidate (if known)"
            },
        },
    },
)


SEND_EMAIL_TOOL = FunctionTool(
    name="send_outreach_email",
    description="Send a personalized outreach email to a candidate. Use this to contact candidates about job opportunities.",
    parameters={
        "type": "object",
        "properties": {
            "candidate_name": {
                "type": "string",
                "description": "Full name of the candidate"
            },
            "candidate_email": {
                "type": "string",
                "description": "Email address of the candidate (optional, will be looked up if not provided)"
            },
            "subject": {
                "type": "string",
                "description": "Email subject line"
            },
            "body": {
                "type": "string",
                "description": "Email body content - personalized message to the candidate"
            },
        },
        "required": ["candidate_name", "subject", "body"],
    },
)
