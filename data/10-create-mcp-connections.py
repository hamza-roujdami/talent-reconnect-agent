#!/usr/bin/env python
"""Create MCP project connections for Foundry IQ Knowledge Bases.

This creates RemoteTool connections in the Foundry project pointing to the
Knowledge Base MCP endpoints. Agents can then use MCPTool to query them.

Usage:
    python data/10-create-mcp-connections.py
    
Prerequisites:
    - Knowledge bases created via 09-create-knowledge-bases.py
    - Project managed identity assigned Search Index Data Reader on search service
"""

import os
import requests
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

load_dotenv()

# Configuration
SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "https://nkg3search.search.windows.net")
PROJECT_RESOURCE_ID = os.environ.get("PROJECT_RESOURCE_ID", "")
API_VERSION = "2025-11-01-preview"

# Knowledge bases to connect
KNOWLEDGE_BASES = [
    {
        "name": "resumes-kb",
        "connection_name": "resumes-kb-mcp",
        "description": "MCP connection to resumes knowledge base"
    },
    {
        "name": "feedback-kb", 
        "connection_name": "feedback-kb-mcp",
        "description": "MCP connection to feedback knowledge base"
    }
]


def get_mcp_endpoint(kb_name: str) -> str:
    """Get the MCP endpoint URL for a knowledge base."""
    return f"{SEARCH_ENDPOINT}/knowledgebases/{kb_name}/mcp?api-version={API_VERSION}"


def create_project_connection(kb_name: str, connection_name: str) -> bool:
    """Create a RemoteTool project connection for a knowledge base.
    
    Args:
        kb_name: Knowledge base name in Azure AI Search
        connection_name: Name for the project connection
        
    Returns:
        True if successful
    """
    if not PROJECT_RESOURCE_ID:
        print("⚠️  PROJECT_RESOURCE_ID not set. Skip connection creation.")
        print("   Set it to your Foundry project ARM resource ID:")
        print("   /subscriptions/.../resourceGroups/.../providers/Microsoft.MachineLearningServices/workspaces/.../projects/...")
        return False
    
    mcp_endpoint = get_mcp_endpoint(kb_name)
    
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(credential, "https://management.azure.com/.default")
    
    url = f"https://management.azure.com{PROJECT_RESOURCE_ID}/connections/{connection_name}?api-version=2025-10-01-preview"
    
    headers = {
        "Authorization": f"Bearer {token_provider()}",
        "Content-Type": "application/json"
    }
    
    body = {
        "name": connection_name,
        "type": "Microsoft.MachineLearningServices/workspaces/connections",
        "properties": {
            "authType": "ProjectManagedIdentity",
            "category": "RemoteTool",
            "target": mcp_endpoint,
            "isSharedToAll": True,
            "audience": "https://search.azure.com/",
            "metadata": {"ApiType": "Azure"}
        }
    }
    
    try:
        response = requests.put(url, headers=headers, json=body)
        
        if response.status_code in [200, 201]:
            print(f"✓ Created connection: {connection_name} -> {kb_name}")
            return True
        else:
            print(f"✗ Failed to create {connection_name}: {response.status_code}")
            print(f"  {response.text[:300]}")
            return False
            
    except Exception as e:
        print(f"✗ Error creating {connection_name}: {e}")
        return False


def list_connections():
    """List existing project connections."""
    if not PROJECT_RESOURCE_ID:
        return []
    
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(credential, "https://management.azure.com/.default")
    
    url = f"https://management.azure.com{PROJECT_RESOURCE_ID}/connections?api-version=2025-10-01-preview"
    
    headers = {
        "Authorization": f"Bearer {token_provider()}",
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("value", [])
    except:
        pass
    return []


def main():
    print(f"Search endpoint: {SEARCH_ENDPOINT}")
    print(f"Project: {PROJECT_RESOURCE_ID[:80]}..." if PROJECT_RESOURCE_ID else "Project: (not set)")
    print()
    
    if not PROJECT_RESOURCE_ID:
        print("⚠️  PROJECT_RESOURCE_ID not set in .env")
        print()
        print("To find it:")
        print("  1. Go to Azure Portal > Your Foundry Project")
        print("  2. Copy the Resource ID from Properties")
        print("  3. Add to .env: PROJECT_RESOURCE_ID=/subscriptions/...")
        print()
        print("Skipping connection creation. You can still use the MCP endpoints manually.")
        print()
        print("MCP Endpoints:")
        for kb in KNOWLEDGE_BASES:
            print(f"  - {kb['name']}: {get_mcp_endpoint(kb['name'])}")
        return
    
    # List existing connections
    existing = list_connections()
    remote_tools = [c for c in existing if c.get("properties", {}).get("category") == "RemoteTool"]
    if remote_tools:
        print(f"Existing RemoteTool connections: {[c['name'] for c in remote_tools]}")
    else:
        print("No existing RemoteTool connections")
    print()
    
    # Create connections for each KB
    print("=== Creating MCP Connections ===")
    for kb in KNOWLEDGE_BASES:
        create_project_connection(kb["name"], kb["connection_name"])
    
    print()
    print("Done! MCP connections created.")
    print()
    print("Foundry IQ is ready. Agents in factory.py use MCPTool with these connections.")


if __name__ == "__main__":
    main()
