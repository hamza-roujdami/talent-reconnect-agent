"""
Talent Reconnect Workflow - MAF WorkflowBuilder with HITL

Uses TurnManager pattern with 2 HITL checkpoints:
1. After JD generation → "proceed or modify?"
2. After resume matching → "send emails to X candidates?"
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

from agent_framework import (
    WorkflowBuilder,
    WorkflowContext,
    Executor,
    handler,
    response_handler,
)
from agent_framework.openai import OpenAIChatClient

from agents import (
    create_jd_generator_agent,
    create_resume_matcher_agent,
    create_outreach_agent,
)

load_dotenv()


@dataclass
class HITLRequest:
    """Request for human input at workflow checkpoint"""
    step: str           # "welcome", "jd", "match"
    step_num: int       # 1, 2, 3
    output: str         # Agent output to display
    prompt: str         # Question for user
    job_title: Optional[str] = None
    jd_content: Optional[str] = None


class TalentReconnectExecutor(Executor):
    """
    MAF Executor that orchestrates the 3-step talent acquisition flow.
    
    Flow:
    1. User provides job role → JD Agent generates description → HITL pause
    2. User says "proceed" → Matcher Agent searches resumes → HITL pause  
    3. User says "send emails" → Outreach Agent sends emails → Done
    """
    
    def __init__(self, chat_client: OpenAIChatClient):
        super().__init__(id="talent_reconnect_executor")
        
        # Create the 3 specialized agents
        self.jd_agent = create_jd_generator_agent(chat_client)
        self.matcher_agent = create_resume_matcher_agent(chat_client)
        self.outreach_agent = create_outreach_agent(chat_client)
        
        # State tracking
        self.job_title: Optional[str] = None
        self.current_jd: Optional[str] = None
        self.current_table: Optional[str] = None
    
    @handler
    async def start(self, user_input: str, ctx: WorkflowContext) -> None:
        """
        Entry point - handles initial greeting or job role input.
        """
        input_lower = user_input.lower().strip()
        
        # Handle greetings
        if input_lower in ["hi", "hello", "hey", "start", ""]:
            welcome_message = """👋 **Welcome to Talent Reconnect!**

I'm your AI-powered talent acquisition assistant powered by **Microsoft Agent Framework**.

I'll help you through a 3-step workflow:
1. 📋 **Generate Job Description** - I'll create a detailed JD from a role name
2. 🔍 **Search & Match Candidates** - Find top 5 matching candidates in a comparison table
3. 📧 **Send Outreach Emails** - Personalized emails to your selected candidates

**What job role are you hiring for?** (e.g., "AI Engineer", "Data Engineer", "ML Engineer")"""
            
            # HITL Pause: Wait for job role
            await ctx.request_info(
                request_data=HITLRequest(
                    step="welcome",
                    step_num=0,
                    output=welcome_message,
                    prompt="Enter job role"
                ),
                response_type=str
            )
            return
        
        # User provided a job role directly - generate JD
        await self._generate_jd(user_input, ctx)
    
    async def _generate_jd(self, job_role: str, ctx: WorkflowContext) -> None:
        """Generate JD and pause for user approval"""
        self.job_title = job_role
        
        print(f"\n⚙️  Step 1/3: Generating JD for '{job_role}'...")
        
        # Run JD Generator Agent
        result = await self.jd_agent.run(f"Generate a job description for: {job_role}")
        self.current_jd = result.text
        
        # HITL Pause: Wait for "proceed" or modifications
        await ctx.request_info(
            request_data=HITLRequest(
                step="jd",
                step_num=1,
                output=result.text,
                prompt="Let me know if you'd like to make any changes, or say 'proceed' to fetch resumes",
                job_title=self.job_title,
                jd_content=self.current_jd
            ),
            response_type=str
        )
    
    async def _search_resumes(self, ctx: WorkflowContext) -> None:
        """Search resumes and show comparison table"""
        print(f"\n⚙️  Step 2/3: Searching resumes for '{self.job_title}'...")
        
        # Run Resume Matcher Agent
        result = await self.matcher_agent.run(f"""
Based on this job description, search for matching candidates:

{self.current_jd}

Job Title: {self.job_title}
""")
        self.current_table = result.text
        
        # HITL Pause: Wait for "send emails to X candidates"
        await ctx.request_info(
            request_data=HITLRequest(
                step="match",
                step_num=2,
                output=result.text,
                prompt="Ready to send outreach? Say 'send emails to top X candidates'",
                job_title=self.job_title,
                jd_content=self.current_jd
            ),
            response_type=str
        )
    
    async def _send_outreach(self, user_request: str, ctx: WorkflowContext) -> None:
        """Send outreach emails and complete workflow"""
        print(f"\n⚙️  Step 3/3: Sending outreach emails...")
        
        # Run Outreach Agent
        result = await self.outreach_agent.run(f"""
Send outreach emails for the {self.job_title} position.

User request: {user_request}

Available candidates from the search:
{self.current_table}
""")
        
        # Workflow complete - yield final output
        await ctx.yield_output(result.text)
    
    @response_handler
    async def on_user_response(
        self,
        original_request: HITLRequest,
        user_input: str,
        ctx: WorkflowContext,
    ) -> None:
        """
        Handle user responses at each HITL checkpoint.
        Routes to appropriate next step based on current state.
        """
        input_lower = user_input.lower().strip()
        
        # Step 0: Welcome → User provided job role
        if original_request.step == "welcome":
            await self._generate_jd(user_input, ctx)
            return
        
        # Step 1: JD Generated → User says "proceed" or wants modifications
        if original_request.step == "jd":
            if input_lower in ["proceed", "continue", "yes", "ok", "looks good", "fetch resumes", "search"]:
                await self._search_resumes(ctx)
            else:
                # User wants to modify JD
                print(f"\n⚙️  Modifying JD based on feedback...")
                result = await self.jd_agent.run(f"""
Update the job description for {self.job_title} with these changes: {user_input}

Original JD:
{self.current_jd}
""")
                self.current_jd = result.text
                
                # Ask again
                await ctx.request_info(
                    request_data=HITLRequest(
                        step="jd",
                        step_num=1,
                        output=result.text,
                        prompt="Let me know if you'd like more changes, or say 'proceed' to fetch resumes",
                        job_title=self.job_title,
                        jd_content=self.current_jd
                    ),
                    response_type=str
                )
            return
        
        # Step 2: Table shown → User says "send emails to X"
        if original_request.step == "match":
            if any(kw in input_lower for kw in ["send", "email", "contact", "reach out", "outreach"]):
                await self._send_outreach(user_input, ctx)
            elif input_lower in ["new search", "start over", "hi", "reset"]:
                # Start over
                await ctx.request_info(
                    request_data=HITLRequest(
                        step="welcome",
                        step_num=0,
                        output="Starting a new search...\n\n**What job role are you hiring for?**",
                        prompt="Enter job role"
                    ),
                    response_type=str
                )
            else:
                # Unknown input - ask again
                await ctx.request_info(
                    request_data=HITLRequest(
                        step="match",
                        step_num=2,
                        output=f"I have {self.current_table[:200]}...\n\n(table truncated)",
                        prompt="Say 'send emails to top X candidates' to proceed, or 'new search' to start over",
                        job_title=self.job_title
                    ),
                    response_type=str
                )


def create_talent_reconnect_workflow():
    """
    Create the MAF workflow with TurnManager-style HITL pattern.
    
    Returns a Workflow instance that can be run with:
        events = await workflow.run("hi")
        events = await workflow.send_responses({request_id: "AI Engineer"})
    """
    # Connect to Compass LLM
    chat_client = OpenAIChatClient(
        model_id=os.getenv("COMPASS_MODEL", "gpt-4.1"),
        api_key=os.getenv("COMPASS_API_KEY"),
        base_url=os.getenv("COMPASS_BASE_URL", "https://api.core42.ai/v1")
    )
    
    # Create executor
    executor = TalentReconnectExecutor(chat_client)
    
    # Build workflow with single executor (handles all HITL internally)
    workflow = (
        WorkflowBuilder(
            name="TalentReconnectWorkflow",
            description="3-step talent acquisition with HITL checkpoints"
        )
        .set_start_executor(executor)
        .build()
    )
    
    return workflow
