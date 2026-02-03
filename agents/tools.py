"""FunctionTool definitions for agents.

Search and feedback use built-in AzureAISearchAgentTool.
Only email tool is custom FunctionTool.
"""

from azure.ai.projects.models import FunctionTool


# Only email remains as custom FunctionTool
# Search/feedback use built-in AzureAISearchAgentTool

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
