"""
Talent Reconnect Supervisor - Interactive Workflow with Human-in-the-Loop

Pattern: WorkflowBuilder with TurnManager executor for step-by-step approval
Based on: learn/workflows/human-in-the-loop/guessing_game_with_human_input.py
"""

import os
import asyncio
from typing import Never
from dataclasses import dataclass
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from agent_framework import (
    AgentExecutorResponse,
    WorkflowBuilder,
    WorkflowContext,
    Executor,
    handler,
    response_handler,
    executor,
)
from agent_framework.openai import OpenAIChatClient

from .skill_mapping_agent import create_skill_mapping_agent
from .resume_sourcing_agent import create_resume_sourcing_agent
from .historical_feedback_agent import create_historical_feedback_agent
from .profile_enricher_agent import create_profile_enricher_agent
from .ta_approval_hitl_agent import create_ta_approval_agent
from .outreach_agent import create_outreach_agent

load_dotenv()


# Define approval request dataclass
@dataclass
class StepApprovalRequest:
    """Request for HR approval to proceed to next step"""
    step_name: str
    step_num: int
    output: str
    prompt: str


class TurnManager(Executor):
    """
    Manages the interactive workflow with human approval between steps.
    
    Responsibilities:
    - Run each agent in sequence
    - After each agent completes, request HR approval
    - On approval, proceed to next agent
    - Repeat for all 6 steps
    """
    
    def __init__(self, agents: list):
        super().__init__(id="turn_manager")
        self.agents = agents
        self.current_step = 0
        self.conversation_history = []
        self.step_results = []
    
    @handler
    async def start(self, job_request: str, ctx: WorkflowContext[AgentExecutorResponse]) -> None:
        """Start the workflow with the initial job description"""
        print(f"\n💬 HR Request received")
        print(f"\n{'='*60}")
        print("Starting Interactive 6-Step Workflow")
        print(f"{'='*60}\n")
        
        # Store initial request
        self.conversation_history = [job_request]
        self.current_step = 0
        
        # Run first agent
        await self._run_current_agent(job_request, ctx)
    
    async def _run_current_agent(self, message: str, ctx: WorkflowContext[AgentExecutorResponse]) -> None:
        """Run the current agent and request approval"""
        if self.current_step >= len(self.agents):
            # All steps complete
            await ctx.yield_output("All 6 steps completed!")
            return
        
        step_name, agent = self.agents[self.current_step]
        step_num = self.current_step + 1
        
        print(f"\n{'='*60}\n⚙️  Step {step_num}/6: {step_name}\n{'='*60}\n")
        
        # Run the agent
        result = await agent.run(message)
        
        # Store result
        self.step_results.append(result)
        
        # Show output
        print(f"\n✅ {step_name} complete\n{'-'*60}")
        print(result.text)
        print(f"{'-'*60}\n")
        
        # Request approval (except for last step)
        if step_num < 6:
            approval_request = StepApprovalRequest(
                step_name=step_name,
                step_num=step_num,
                output=result.text,
                prompt=f"Type 'continue' to proceed to Step {step_num + 1}/6"
            )
            await ctx.request_info(
                request_data=approval_request,
                response_type=str
            )
        else:
            # Last step - ask for final confirmation
            approval_request = StepApprovalRequest(
                step_name=step_name,
                step_num=step_num,
                output=result.text,
                prompt="Type 'email' or 'message' to confirm outreach method"
            )
            await ctx.request_info(
                request_data=approval_request,
                response_type=str
            )
    
    @response_handler
    async def on_approval(
        self,
        original_request: StepApprovalRequest,
        user_input: str,
        ctx: WorkflowContext[AgentExecutorResponse, str],
    ) -> None:
        """Handle HR approval and continue to next step"""
        print(f"✅ HR approved: '{user_input}'\n")
        
        # Move to next step
        self.current_step += 1
        
        # Check if workflow is complete
        if self.current_step >= len(self.agents):
            final_result = self.step_results[-1].text if self.step_results else "Workflow completed"
            await ctx.yield_output(final_result)
            return
        
        # Get text from last result to pass as context
        last_result = self.step_results[-1]
        
        # Continue to next agent with previous result as context
        await self._run_current_agent(last_result.text, ctx)


class SupervisorWorkflow:
    """
    Interactive 6-step workflow with human approval between each step.
    
    Uses MAF WorkflowBuilder with TurnManager executor for HITL.
    Each step pauses and waits for human "continue" before proceeding.
    """
    
    def __init__(self):
        print("🔧 Initializing Interactive Workflow with Human-in-the-Loop...")
        
        # Connect to Azure OpenAI
        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        
        chat_client = OpenAIChatClient(
            model_id=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini-deployment"),
            api_key=token.token,
            base_url=os.getenv("OPENAI_API_BASE")
        )
        
        # Create all 6 agents with their names
        agents = [
            ("1️⃣ Skills Mapping", create_skill_mapping_agent(chat_client)),
            ("2️⃣ Resume Sourcing", create_resume_sourcing_agent(chat_client)),
            ("3️⃣ Historical Feedback", create_historical_feedback_agent(chat_client)),
            ("4️⃣ Profile Enrichment", create_profile_enricher_agent(chat_client)),
            ("5️⃣ TA Approval (HITL)", create_ta_approval_agent(chat_client)),
            ("6️⃣ Outreach Generation", create_outreach_agent(chat_client))
        ]
        
        # Create TurnManager to orchestrate agents with approval
        turn_manager = TurnManager(agents=agents)
        
        # Build simple workflow: just the TurnManager
        self.workflow = (
            WorkflowBuilder()
            .set_start_executor(turn_manager)
            .build()
        )
        
        print("✅ Workflow ready with 6 interactive steps\n")
    
    async def route(self, user_message: str) -> str:
        """
        Run workflow with human-in-the-loop approval at each step.
        
        Flow:
        1. HR provides job description
        2. TurnManager runs Step 1, requests approval
        3. HR types "continue"
        4. TurnManager runs Step 2, requests approval
        ... repeats for all 6 steps
        6. Final step asks for "email" or "message" confirmation
        """
        
        # Loop to handle approval requests
        responses: dict[str, str] = {}
        output = None
        
        while True:
            # Run workflow or send approval responses
            if responses:
                events = await self.workflow.send_responses(responses)
                responses.clear()
            else:
                events = await self.workflow.run(user_message)
            
            # Check for approval requests
            request_info_events = events.get_request_info_events()
            for request_info_event in request_info_events:
                if not isinstance(request_info_event.data, StepApprovalRequest):
                    continue
                
                approval_request = request_info_event.data
                
                # Display approval prompt
                print(f"\n{'='*60}")
                print(f"⏸️  WAITING FOR HR APPROVAL")
                print(f"{'='*60}")
                print(f"\n📋 {approval_request.step_name} completed")
                print(f"📊 Progress: Step {approval_request.step_num}/6")
                print(f"\n{approval_request.prompt}")
                print(f"{'='*60}\n")
                
                # For demo, auto-approve
                # In production Gradio UI, this would wait for actual user input
                print("✅ Auto-approving for demo (will be interactive in Gradio UI)\n")
                if approval_request.step_num == 6:
                    responses[request_info_event.request_id] = "email"
                else:
                    responses[request_info_event.request_id] = "continue"
            
            # Check if workflow completed
            if outputs := events.get_outputs():
                output = outputs[0]
                break
        
        if not output:
            return "Workflow completed without output"
        
        print(f"\n{'='*60}")
        print("✅ WORKFLOW COMPLETED - All 6 steps approved")
        print(f"{'='*60}\n")
        
        return output


def create_supervisor():
    return SupervisorWorkflow()


async def test_supervisor():
    """
    Test the workflow - runs all 6 steps automatically for now.
    
    Next step: Add approval requests between steps so HR can review
    each step's output before proceeding with "continue".
    """
    supervisor = create_supervisor()
    
    test_query = """I need to find candidates for a Senior Machine Learning Engineer role.

Job Requirements:
- 5+ years experience in Python and machine learning
- Hands-on experience with Azure ML and MLOps practices
- Strong leadership and team collaboration skills
- Proven track record building production ML systems
- Experience with cloud platforms (Azure preferred)

Company: TechCorp Solutions
Location: Remote or San Francisco Bay Area"""
    
    print(f"\n{'='*60}\nTEST: Interactive Workflow\n{'='*60}")
    response = await supervisor.route(test_query)
    print(f"\n💬 Final Response:\n{response}\n")


if __name__ == "__main__":
    asyncio.run(test_supervisor())
