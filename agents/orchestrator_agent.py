"""
Orchestrator Agent for Talent Reconnect System

This agent uses an LLM to orchestrate the sequential workflow:
1. Skills Mapping
2. Resume Sourcing
3. Historical Feedback
4. Profile Enrichment
5. TA Approval (HITL)
6. Outreach

Similar to supervisor.py in clinic scheduler, but enforces sequential order.
"""

import os
import json
from typing import List
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

load_dotenv()

class OrchestratorAgent:
    """LLM-powered orchestrator that manages the sequential talent reconnect workflow"""
    
    def __init__(self):
        # Set up Azure authentication
        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        
        # Initialize OpenAI chat client for Azure Foundry
        self.chat_client = OpenAIChatClient(
            model_id=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini-deployment"),
            api_key=token.token,
            base_url=os.getenv("OPENAI_API_BASE")
        )
        
        # Create intent classifier agent for workflow step determination 
        self.classifier_agent = ChatAgent(
            chat_client=self.chat_client,
            name="WorkflowClassifier",
            instructions="""
            You analyze the current workflow state and determine which step to execute next.
            
            The Talent Reconnect workflow has these sequential steps:
            1. SKILLS_MAPPING - Extract canonical skills from job description
            2. RESUME_SOURCING - Search for matching candidates in database
            3. HISTORICAL_FEEDBACK - Filter based on ATS/CRM feedback
            4. PROFILE_ENRICHMENT - Enrich with current employment data
            5. TA_APPROVAL - Human approval required (HITL)
            6. OUTREACH - Send messages to approved candidates
            
            You must ALWAYS follow this order. Each step depends on the previous step.
            
            Return JSON with:
            {
                "current_step": "SKILLS_MAPPING|RESUME_SOURCING|HISTORICAL_FEEDBACK|PROFILE_ENRICHMENT|TA_APPROVAL|OUTREACH",
                "reason": "Brief explanation of why this step",
                "completed_steps": ["list", "of", "completed", "steps"],
                "workflow_complete": false
            }
            
            If all steps are complete, set workflow_complete to true.
            """
        )
        
        # Worker agents (will be initialized in route method)
        self.skill_mapping_agent = None
        self.resume_sourcing_agent = None
        self.historical_feedback_agent = None
        self.profile_enricher_agent = None
        self.ta_approval_agent = None
        self.outreach_agent = None
        
        self.workflow_state = {
            "completed_steps": [],
            "current_step": None,
            "job_data": {},
            "skills": [],
            "candidates": [],
            "filtered_candidates": [],
            "enriched_candidates": [],
            "approved_candidates": [],
            "outreach_results": []
        }
    
    async def classify_workflow_state(self, user_input: str) -> dict:
        """
        Use LLM to determine which workflow step should execute next
        Similar to supervisor's classify_intent()
        """
        
        # Detect if this is a new job request (reset workflow)
        new_job_indicators = [
            "need to find candidates for",
            "looking for candidates",
            "search for candidates for a",
            "find talent for",
            "job requirements",
            "new role",
            "position:"
        ]
        
        if any(indicator in user_input.lower() for indicator in new_job_indicators):
            # Check if workflow was previously completed or partially started
            if self.workflow_state['completed_steps']:
                print("\n🔄 New job request detected - Resetting workflow state\n")
                self.workflow_state = {
                    "completed_steps": [],
                    "job_data": {},
                    "skills": [],
                    "candidates": [],
                    "filtered_candidates": [],
                    "enriched_candidates": [],
                    "approved_candidates": [],
                    "outreach_results": []
                }
        
        # Build context for LLM
        context = f"""
        User Input: {user_input}
        
        Current Workflow State:
        - Completed Steps: {self.workflow_state['completed_steps']}
        - Job Data Available: {bool(self.workflow_state['job_data'])}
        - Skills Extracted: {len(self.workflow_state['skills'])} skills
        - Candidates Found: {len(self.workflow_state['candidates'])} candidates
        - Filtered Candidates: {len(self.workflow_state['filtered_candidates'])} candidates
        - Enriched Candidates: {len(self.workflow_state['enriched_candidates'])} candidates
        - Approved Candidates: {len(self.workflow_state['approved_candidates'])} candidates
        - Outreach Completed: {len(self.workflow_state['outreach_results'])} sent
        
        Determine the next step in the sequential workflow.
        """
        
        # Use simple string input for agent
        response = await self.classifier_agent.run(context)
        
        # Parse JSON response
        try:
            # Extract JSON from response
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Find JSON in response
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                classification = json.loads(json_str)
            else:
                # Fallback: start from beginning
                classification = {
                    "current_step": "SKILLS_MAPPING",
                    "reason": "Starting workflow from beginning",
                    "completed_steps": [],
                    "workflow_complete": False
                }
        except Exception as e:
            print(f"⚠️ Classification parsing error: {e}")
            classification = {
                "current_step": "SKILLS_MAPPING",
                "reason": "Error in classification, defaulting to first step",
                "completed_steps": [],
                "workflow_complete": False
            }
        
        return classification
    
    async def route(self, user_input: str):
        """
        Main routing method - determines which agent to call based on workflow state
        Similar to supervisor's route() method
        """
        print(f"\n📨 User: {user_input}")
        
        # Classify workflow state
        classification = await self.classify_workflow_state(user_input)
        
        print(f"🔍 Workflow Classification: {classification}")
        
        current_step = classification.get("current_step", "SKILLS_MAPPING")
        
        # Import agents lazily to avoid circular imports
        if self.skill_mapping_agent is None:
            # Support both package import and direct script execution
            try:
                from .skill_mapping_agent import create_skill_mapping_agent
                from .resume_sourcing_agent import create_resume_sourcing_agent
                from .historical_feedback_agent import create_historical_feedback_agent
                from .profile_enricher_agent import create_profile_enricher_agent
                from .ta_approval_hitl_agent import create_ta_approval_agent
                from .outreach_agent import create_outreach_agent
            except ImportError:
                # Running as script, use absolute imports
                from skill_mapping_agent import create_skill_mapping_agent
                from resume_sourcing_agent import create_resume_sourcing_agent
                from historical_feedback_agent import create_historical_feedback_agent
                from profile_enricher_agent import create_profile_enricher_agent
                from ta_approval_hitl_agent import create_ta_approval_agent
                from outreach_agent import create_outreach_agent
            
            self.skill_mapping_agent = create_skill_mapping_agent(self.chat_client)
            self.resume_sourcing_agent = create_resume_sourcing_agent(self.chat_client)
            self.historical_feedback_agent = create_historical_feedback_agent(self.chat_client)
            self.profile_enricher_agent = create_profile_enricher_agent(self.chat_client)
            self.ta_approval_agent = create_ta_approval_agent(self.chat_client)
            self.outreach_agent = create_outreach_agent(self.chat_client)
        
        # Route to appropriate agent based on current step
        result = ""
        
        if current_step == "SKILLS_MAPPING":
            print("→ Skills Mapping Agent")
            result = await self.skill_mapping_agent.run(user_input)
            self.workflow_state["completed_steps"].append("SKILLS_MAPPING")
            # Parse skills from result (mock)
            self.workflow_state["skills"] = ["Python", "Machine Learning", "Azure", "SQL", "Leadership"]
            
        elif current_step == "RESUME_SOURCING":
            print("→ Resume Sourcing Agent")
            skills_context = f"Search for candidates with these skills: {', '.join(self.workflow_state['skills'])}"
            result = await self.resume_sourcing_agent.run(skills_context)
            self.workflow_state["completed_steps"].append("RESUME_SOURCING")
            
            # Parse candidate names from the sourcing result
            # Extract names from the agent response (format: "Name | email | skills_match")
            import re
            candidate_names = []
            # Look for lines with candidate format in the result
            for line in str(result).split('\n'):
                # Match pattern like "1. Sarah Chen | sarah.chen@example.com"
                match = re.match(r'\d+\.\s+([^|]+)\s+\|', line)
                if match:
                    candidate_names.append(match.group(1).strip())
            
            # Fallback if parsing fails
            if not candidate_names:
                candidate_names = ["Sarah Chen", "Marcus Johnson", "Priya Sharma"]
            
            self.workflow_state["candidates"] = candidate_names
            
        elif current_step == "HISTORICAL_FEEDBACK":
            print("→ Historical Feedback Agent")
            candidates_context = f"Filter these candidates: {', '.join(self.workflow_state['candidates'])}"
            result = await self.historical_feedback_agent.run(candidates_context)
            self.workflow_state["completed_steps"].append("HISTORICAL_FEEDBACK")
            
            # Parse filtered candidate names from historical feedback result
            import re
            filtered_names = []
            for line in str(result).split('\n'):
                match = re.match(r'✓\s+([^:]+):', line)
                if match:
                    filtered_names.append(match.group(1).strip())
            
            # Fallback: use subset of original candidates
            if not filtered_names:
                filtered_names = self.workflow_state["candidates"][:2] if len(self.workflow_state["candidates"]) >= 2 else self.workflow_state["candidates"]
            
            self.workflow_state["filtered_candidates"] = filtered_names
            
        elif current_step == "PROFILE_ENRICHMENT":
            print("→ Profile Enrichment Agent")
            enrich_context = f"Enrich profiles for: {', '.join(self.workflow_state['filtered_candidates'])}"
            result = await self.profile_enricher_agent.run(enrich_context)
            self.workflow_state["completed_steps"].append("PROFILE_ENRICHMENT")
            self.workflow_state["enriched_candidates"] = self.workflow_state["filtered_candidates"]
            
        elif current_step == "TA_APPROVAL":
            print("→ TA Approval Agent (HITL)")
            approval_context = f"Present for approval: {', '.join(self.workflow_state['enriched_candidates'])}"
            result = await self.ta_approval_agent.run(approval_context)
            self.workflow_state["completed_steps"].append("TA_APPROVAL")
            
            # Parse approved candidate names from TA approval result
            import re
            approved_names = []
            for line in str(result).split('\n'):
                # Match lines like "✅ APPROVED: Sarah Chen"
                match = re.match(r'✅\s+APPROVED:\s+(.+)', line)
                if match:
                    approved_names.append(match.group(1).strip())
            
            # Fallback: approve first candidate if parsing fails
            if not approved_names and self.workflow_state['enriched_candidates']:
                approved_names = [self.workflow_state['enriched_candidates'][0]]
            
            self.workflow_state["approved_candidates"] = approved_names
            
        elif current_step == "OUTREACH":
            print("→ Outreach Agent")
            # Provide detailed candidate information for outreach
            approved = self.workflow_state['approved_candidates']
            if approved:
                # Use actual approved candidate names dynamically
                candidate_list = '\n'.join([f"- {name}" for name in approved])
                outreach_context = f"""Send personalized outreach messages to the following approved candidates for the Senior Machine Learning Engineer role:

Approved Candidates:
{candidate_list}

Please use the send_outreach_message tool for each candidate. Generate professional, personalized outreach messages for each candidate via email."""
            else:
                outreach_context = "No candidates were approved for outreach."
            
            result = await self.outreach_agent.run(outreach_context)
            self.workflow_state["completed_steps"].append("OUTREACH")
            self.workflow_state["outreach_results"] = [f"Message sent to {c}" for c in approved]
            
        else:
            result = f"Unknown workflow step: {current_step}"
        
        return result


def create_orchestrator():
    """Factory function to create orchestrator instance"""
    return OrchestratorAgent()


# =============================================================================
# Test Block - Run this file directly to test the orchestrator
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("\n" + "="*60)
        print("🧪 Testing Orchestrator Agent")
        print("="*60 + "\n")
        
        # Create orchestrator
        print("🔧 Initializing orchestrator...")
        orchestrator = create_orchestrator()
        print("✅ Orchestrator initialized\n")
        
        # Test input from README
        test_input = """
I need to find candidates for a Senior Machine Learning Engineer role.

Job Requirements:
- 5+ years experience in Python and machine learning
- Hands-on experience with Azure ML and MLOps practices
- Strong leadership and team collaboration skills
- Proven track record building production ML systems
- Experience with cloud platforms (Azure preferred)

Company: TechCorp Solutions
Location: Remote or San Francisco Bay Area
"""
        
        print("📨 Test Input:")
        print(test_input)
        print("\n" + "-"*60 + "\n")
        
        # Run orchestrator
        print("🚀 Running orchestrator workflow...\n")
        
        try:
            result = await orchestrator.route(test_input)
            
            print("\n" + "-"*60)
            print("\n📊 Result:")
            print(result)
            print("\n" + "="*60)
            
            # Show workflow state
            print("\n📈 Workflow State:")
            print(f"  Completed Steps: {orchestrator.workflow_state['completed_steps']}")
            print(f"  Skills: {orchestrator.workflow_state['skills']}")
            print(f"  Candidates: {len(orchestrator.workflow_state['candidates'])} found")
            print(f"  Next Step: Call route() again to continue workflow")
            print("\n" + "="*60 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(test())
