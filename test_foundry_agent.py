"""
Foundry Agent Service Test - Full Workflow

Tests creating a Foundry agent with Azure AI Search and running conversations.

This uses the Azure AI Projects SDK v2 pattern:
1. Create agent definition with create_version()
2. Use get_openai_client().responses.create() for conversations
3. Pass agent reference in extra_body

Usage:
    python test_foundry_agent.py

Prerequisites:
    - AZURE_AI_PROJECT_ENDPOINT in .env (project endpoint, not hub)
    - Azure AI Search connection configured in Foundry project
    - resumes index populated
"""
import os
from dotenv import load_dotenv

load_dotenv()


def test_foundry_agent():
    """Test Foundry Agent Service with Azure AI Search."""
    from azure.identity import DefaultAzureCredential
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import (
        PromptAgentDefinition, 
        AzureAISearchAgentTool, 
        AzureAISearchToolResource,
        AISearchIndexResource,
        AzureAISearchQueryType,
    )
    
    # Get configuration
    project_endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    model = os.environ.get("FOUNDRY_MODEL_PRIMARY", "gpt-4o-mini")
    resume_index = os.environ.get("SEARCH_RESUME_INDEX", "resumes")
    
    if not project_endpoint:
        print("❌ AZURE_AI_PROJECT_ENDPOINT not set")
        print("   Set this to your Foundry project endpoint, e.g.:")
        print("   https://your-account.services.ai.azure.com/api/projects/your-project")
        return
    
    print("=" * 60)
    print("🧪 Foundry Agent Service Test")
    print("=" * 60)
    print(f"📍 Project: {project_endpoint}")
    print(f"🤖 Model: {model}")
    print(f"🔍 Search Index: {resume_index}")
    print()
    
    # Create project client
    credential = DefaultAzureCredential()
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=credential,
    )
    
    with project_client:
        # =====================================================================
        # Step 1: List available connections and find Azure AI Search
        # =====================================================================
        print("📋 Step 1: Listing project connections...")
        search_connection_id = None
        
        try:
            connections = list(project_client.connections.list())
            if connections:
                print("   Available connections:")
                for conn in connections:
                    conn_type = getattr(conn, 'connection_type', 'unknown')
                    print(f"   - {conn.name} ({conn_type}): {conn.id}")
                    # Check for Azure AI Search connection
                    if "search" in conn.name.lower() or "AZURE_AI_SEARCH" in str(conn_type).upper():
                        search_connection_id = conn.id
                        print(f"     ✓ Using this for Azure AI Search")
            else:
                print("   ⚠️ No connections found in project")
        except Exception as e:
            print(f"   ⚠️ Could not list connections: {e}")
        
        if not search_connection_id:
            print("\n   💡 To add Azure AI Search connection:")
            print("      1. Go to Azure AI Foundry portal")
            print("      2. Open your project → Management center → Connections")
            print("      3. Add connection → Azure AI Search")
            print("      4. Use your search endpoint and API key")
        print()
        
        # =====================================================================
        # Step 2: Create agent with Azure AI Search tool
        # =====================================================================
        print("🔧 Step 2: Creating agent with Azure AI Search tool...")
        
        # Build tools list
        tools = []
        
        if search_connection_id:
            # Create the index resource
            index_resource = AISearchIndexResource(
                project_connection_id=search_connection_id,
                index_name=resume_index,
                query_type=AzureAISearchQueryType.SEMANTIC,
                top_k=10,
            )
            # Wrap in tool resource and then tool
            ai_search_tool = AzureAISearchAgentTool(
                azure_ai_search=AzureAISearchToolResource(
                    indexes=[index_resource]
                )
            )
            tools.append(ai_search_tool)
            print(f"   ✓ Azure AI Search tool configured for '{resume_index}'")
        else:
            print("   ⚠️ No search connection - agent will use base knowledge only")
        
        # Define agent instructions
        instructions = """You are a helpful recruiting assistant for Talent Reconnect.

Your job is to help recruiters find and connect with candidates.

You have access to an Azure AI Search index containing resumes. When users ask about 
finding candidates, use the search tool to find matching profiles.

When presenting candidates:
1. Show their name, current title, company, and location
2. Highlight relevant skills and experience
3. Note years of experience
4. If asked for details, provide more comprehensive information

Be concise and professional. Focus on actionable information."""

        # Create agent version (this is the new pattern)
        try:
            agent = project_client.agents.create_version(
                agent_name="talent-reconnect-agent",
                definition=PromptAgentDefinition(
                    model=model,
                    instructions=instructions,
                    tools=tools,
                ),
            )
            print(f"   ✓ Agent created: {agent.name} (version: {agent.version})")
        except Exception as e:
            print(f"   ❌ Failed to create agent: {e}")
            print("   Trying alternative create method...")
            
            # Fallback to simple create
            agent = project_client.agents.create(
                agent_name="talent-reconnect-agent",
                model=model,
                instructions=instructions,
            )
            print(f"   ✓ Agent created (fallback): {agent.name}")
        print()
        
        # =====================================================================
        # Step 3: Test conversations using OpenAI Responses API
        # =====================================================================
        print("💬 Step 3: Testing agent with queries...")
        
        # Get OpenAI client for responses
        openai_client = project_client.get_openai_client()
        
        test_queries = [
            "Find Data Engineers in Dubai with Azure experience",
            "Show me the top 3 candidates with Python skills",
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n   Query {i}: {query}")
            print("   " + "-" * 50)
            
            try:
                # Use Responses API with agent reference
                response = openai_client.responses.create(
                    input=query,
                    extra_body={
                        "agent": {
                            "name": agent.name,
                            "type": "agent_reference",
                        }
                    },
                )
                
                # Extract response text
                response_text = response.output_text if hasattr(response, 'output_text') else str(response)
                
                # Truncate long responses for display
                if len(response_text) > 800:
                    response_text = response_text[:800] + "..."
                    
                print(f"   🤖 Response:\n   {response_text}")
                
            except Exception as e:
                print(f"   ❌ Query failed: {e}")
        
        # =====================================================================
        # Step 4: Cleanup
        # =====================================================================
        print("\n🧹 Step 4: Cleaning up...")
        try:
            project_client.agents.delete_version(
                agent_name=agent.name,
                agent_version=agent.version,
            )
            print(f"   ✓ Agent deleted")
        except Exception as e:
            print(f"   ⚠️ Cleanup failed: {e}")
        
        print("\n" + "=" * 60)
        print("✅ Foundry Agent Service test completed!")
        print("=" * 60)


if __name__ == "__main__":
    test_foundry_agent()
