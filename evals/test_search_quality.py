"""Search Quality Evaluation using Azure AI Search context grounding."""
import asyncio
import json
import sys
from pathlib import Path

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from tools.search_provider import build_search_context_provider

API_VERSION = "2024-10-21"


def load_golden_dataset():
    """Load test queries from golden dataset."""
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path) as f:
        return json.load(f)


def extract_skills_from_result(result_text: str) -> set:
    """Extract skills mentioned in a search result."""
    # Simple keyword extraction - in production use NER
    common_skills = [
        "python", "javascript", "typescript", "react", "node.js", "nodejs",
        "aws", "azure", "gcp", "docker", "kubernetes", "k8s",
        "pytorch", "tensorflow", "machine learning", "ml", "ai",
        "django", "fastapi", "flask", "express",
        "sql", "postgresql", "mongodb", "redis",
        "nlp", "transformers", "bert", "gpt",
        "java", "go", "rust", "c++",
    ]
    result_lower = result_text.lower()
    return {skill for skill in common_skills if skill in result_lower}


def calculate_precision(results: str, expected_skills: list) -> float:
    """Calculate precision based on skill overlap."""
    if not results or results == "No matching candidates found.":
        return 0.0
    
    expected_set = {s.lower() for s in expected_skills}
    found_skills = extract_skills_from_result(results)
    
    if not found_skills:
        return 0.0
    
    overlap = found_skills & expected_set
    return len(overlap) / len(expected_set) if expected_set else 0.0


def _create_chat_client() -> AzureOpenAIChatClient:
    llm = config.llm
    if llm.provider != "azure_openai":
        raise RuntimeError("Search quality eval requires Azure OpenAI configuration.")

    if llm.use_entra_id:
        credential = DefaultAzureCredential()
        return AzureOpenAIChatClient(
            endpoint=llm.azure_endpoint,
            deployment_name=llm.azure_deployment,
            credential=credential,
            api_version=API_VERSION,
        )

    if not llm.api_key:
        raise RuntimeError("AZURE_OPENAI_KEY is required when not using Entra ID auth.")

    return AzureOpenAIChatClient(
        endpoint=llm.azure_endpoint,
        deployment_name=llm.azure_deployment,
        api_key=llm.api_key,
        api_version=API_VERSION,
    )


async def semantic_search_response(prompt: str) -> str:
    provider = build_search_context_provider()
    async with provider:
        chat_client = _create_chat_client()
        agent: ChatAgent = chat_client.create_agent(
            name="search_eval_probe",
            instructions=(
                "You are evaluating resume relevance. Answer using the Azure AI Search "
                "context and include short bullet points with citations."
            ),
            temperature=0.2,
            context_providers=[provider],
        )

        chunks: list[str] = []
        async for event in agent.run_stream(prompt):
            if hasattr(event, "text") and event.text:
                chunks.append(event.text)

        return "".join(chunks).strip()


async def run_semantic_batch(queries: list[str]) -> list[str]:
    responses: list[str] = []
    for query in queries:
        responses.append(await semantic_search_response(query))
    return responses


def run_search_eval():
    """Run search quality evaluation using semantic grounding."""
    print("=" * 60)
    print("Search Quality Evaluation")
    print("=" * 60)

    dataset = load_golden_dataset()
    queries = dataset["search_queries"]

    prompts = [q["query"] for q in queries]
    semantic_results = asyncio.run(run_semantic_batch(prompts))

    semantic_scores = []

    for query_data, result_text in zip(queries, semantic_results):
        query = query_data["query"]
        expected_skills = query_data["relevant_skills"]

        print(f"\n📝 Query: {query}")
        print(f"   Expected skills: {', '.join(expected_skills)}")

        semantic_precision = calculate_precision(result_text, expected_skills)
        semantic_scores.append(semantic_precision)

        print(f"   Semantic Precision: {semantic_precision:.0%}")

    avg_semantic = sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Average Semantic Precision: {avg_semantic:.0%}")

    return {
        "semantic_avg_precision": avg_semantic,
    }


if __name__ == "__main__":
    run_search_eval()
