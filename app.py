"""
Talent Reconnect Agent - Gradio Web UI

AI-powered talent acquisition system that:
1. Maps job descriptions to canonical skills
2. Searches internal resumes via Azure AI Search
3. Applies historical ATS/CRM feedback
4. Enriches profiles with current employment data
5. Requires TA manager approval (HITL)
6. Sends outreach messages to approved candidates
"""

import os
import asyncio
import gradio as gr
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Lazy-load orchestrator to avoid circular imports
_orchestrator = None

def get_orchestrator():
    """Lazy initialization of orchestrator"""
    global _orchestrator
    if _orchestrator is None:
        print("🚀 Initializing Talent Reconnect System...")
        from agents.orchestrator_agent import create_orchestrator
        _orchestrator = create_orchestrator()
        print("✅ System Ready")
    return _orchestrator


async def chat(message, history):
    """
    Handle chat messages and route through orchestrator
    """
    try:
        orchestrator = get_orchestrator()
        
        # Route message through orchestrator (history handled internally)
        response = await orchestrator.route(message)
        
        # Extract text from AgentRunResponse
        if hasattr(response, 'text'):
            response_text = response.text
        elif hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)
        
        # Return updated history (Gradio Chatbot expects list of message dicts with 'role' and 'content')
        history = history or []
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response_text})
        return history
    
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}\n\nPlease check your Azure credentials in .env file."
        history = history or []
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
        return history


# Create Gradio interface
with gr.Blocks(title="Talent Reconnect Agent") as demo:
    gr.Markdown(
        """
        # 🎯 Talent Reconnect Agent
        
        **AI-Powered Talent Acquisition System**
        """
    )
    
    chatbot = gr.Chatbot(
        label="Talent Reconnect Workflow",
        height=500
    )
    
    msg = gr.Textbox(
        label="Your Message",
        placeholder="Example: I need to find candidates for a Senior ML Engineer role...",
        lines=3
    )
    
    with gr.Row():
        submit = gr.Button("Send", variant="primary")
        clear = gr.Button("Clear")
    
    gr.Markdown(
        """
        ### 🧪 Example Prompts:
        
        **Full Workflow:**
        - "I need to find candidates for a Senior Machine Learning Engineer role. The job requires Python, Azure ML, MLOps experience, and leadership skills."
        
        **Step-by-Step:**
        - "Extract skills from this job: Senior Data Scientist with 5+ years in Python, ML, and cloud platforms"
        - "Search for candidates with Python, Machine Learning, and Azure skills"
        - "Check historical feedback for Sarah Chen and Marcus Johnson"
        - "Enrich profile for Sarah Chen"
        - "Present candidates for TA manager approval"
        - "Send outreach to approved candidates"
        
        ### 📊 Workflow Steps:
        
        1. **Skills Mapping** - Extracts canonical skills from job description
        2. **Resume Sourcing** - Searches Azure AI Search for matching candidates
        3. **Historical Feedback** - Filters based on ATS/CRM interaction history
        4. **Profile Enrichment** - Adds current employment data via compliant APIs
        5. **TA Approval (HITL)** - Human review and approval required
        6. **Outreach** - Sends messages and logs to ATS/CRM
        
        ---
        *Demo system using mock data. For production: integrate real Azure AI Search, ATS/CRM APIs, and compliant data providers.*
        """
    )
    
    # Event handlers
    submit.click(
        fn=chat,
        inputs=[msg, chatbot],
        outputs=[chatbot]
    ).then(
        lambda: "", None, msg
    )
    
    msg.submit(
        fn=chat,
        inputs=[msg, chatbot],
        outputs=[chatbot]
    ).then(
        lambda: "", None, msg
    )
    
    def reset_conversation():
        """Reset chatbot and orchestrator state"""
        global _orchestrator
        _orchestrator = None  # Force re-initialization on next message
        return None
    
    clear.click(reset_conversation, None, chatbot)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎯 Talent Reconnect Agent")
    print("="*60)
    print("\n🚀 Starting Gradio web interface...")
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,  # Different port from clinic scheduler (7860)
        share=False
    )
