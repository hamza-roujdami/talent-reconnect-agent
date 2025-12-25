#!/usr/bin/env python3
"""Agentic Azure AI Search harness for the resumes index.

Renamed from the Agent Framework sample `azure_ai_with_search_context_agentic.py`
documented at https://learn.microsoft.com/azure/ai-services/agent-framework/reference/python/agent_framework.azure.azureaisearchcontextprovider
so our repo naming aligns with the recruiting workflow.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Iterable, Sequence

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient, AzureAISearchContextProvider
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

# Ensure local env files (.env, .env.local, .emv) are loaded before we inspect os.environ
for env_file in (".env", ".env.local", ".emv"):
    load_dotenv(env_file, override=False)

DEFAULT_PROMPTS: Sequence[str] = (
    "What trends span multiple resumes?",
    "Which profiles connect product and ML experience?",
    "Who would you shortlist for a staff-level data platform role?",
)


def _require_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    joined = " or ".join(names)
    raise RuntimeError(f"Environment variable {joined} is required for this harness.")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test Azure AI Search agentic mode using the Agent Framework sample harness.",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional prompts to run. Defaults to three sample questions when omitted.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=int(os.getenv("AZURE_SEARCH_TOP_K", "4")),
        help="Number of documents to retrieve per hop when using an index (default: 4).",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=("minimal", "low", "medium"),
        default=os.getenv("AZURE_SEARCH_RETRIEVAL_REASONING", "minimal"),
        help="Adjust agentic retrieval reasoning effort (default: minimal).",
    )
    parser.add_argument(
        "--output-mode",
        choices=("extractive_data", "answer_synthesis"),
        default=os.getenv("AZURE_SEARCH_KB_OUTPUT_MODE", "extractive_data"),
        help="Knowledge base output style (default: extractive_data).",
    )
    return parser.parse_args(list(argv))


async def run_agentic_demo(
    prompts: Sequence[str],
    top_k: int,
    reasoning_effort: str,
    output_mode: str,
) -> None:
    search_endpoint = _require_env("SEARCH_SERVICE_ENDPOINT", "AZURE_SEARCH_ENDPOINT")
    search_index = os.getenv("SEARCH_RESUME_INDEX") or os.getenv("AZURE_SEARCH_INDEX_NAME") or os.getenv("AZURE_SEARCH_INDEX")
    knowledge_base_name = os.getenv("SEARCH_KNOWLEDGE_BASE_NAME") or os.getenv("AZURE_SEARCH_KNOWLEDGE_BASE_NAME")
    azure_openai_resource_url = (
        os.getenv("FOUNDRY_CHAT_ENDPOINT")
        or os.getenv("AZURE_OPENAI_RESOURCE_URL")
        or os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    if not knowledge_base_name and not search_index:
        raise RuntimeError(
            "Set AZURE_SEARCH_KNOWLEDGE_BASE_NAME or AZURE_SEARCH_INDEX_NAME before running this harness."
        )

    project_endpoint = _require_env("FOUNDRY_PROJECT_ENDPOINT", "AZURE_AI_PROJECT_ENDPOINT")
    model_deployment = (
        os.getenv("FOUNDRY_MODEL_FAST")
        or os.getenv("FOUNDRY_MODEL_PRIMARY")
        or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        or "gpt-4o-mini"
    )
    search_api_key = (
        os.getenv("SEARCH_SERVICE_API_KEY")
        or os.getenv("AZURE_SEARCH_API_KEY")
        or os.getenv("AZURE_SEARCH_KEY")
    )

    async with DefaultAzureCredential() as credential:
        provider_kwargs = {
            "endpoint": search_endpoint,
            "api_key": search_api_key,
            "credential": None if search_api_key else credential,
            "mode": "agentic",
            "knowledge_base_output_mode": output_mode,
            "retrieval_reasoning_effort": reasoning_effort,
        }

        if knowledge_base_name:
            provider_kwargs["knowledge_base_name"] = knowledge_base_name
        else:
            if not azure_openai_resource_url:
                raise RuntimeError(
                    "Set FOUNDRY_CHAT_ENDPOINT (or legacy AZURE_OPENAI_RESOURCE_URL/AZURE_OPENAI_ENDPOINT) when using an index for agentic mode."
                )
            provider_kwargs.update(
                {
                    "index_name": search_index,
                    "azure_openai_resource_url": azure_openai_resource_url,
                    "model_deployment_name": model_deployment,
                    "top_k": top_k,
                }
            )

        search_provider = AzureAISearchContextProvider(**provider_kwargs)

        async with (
            search_provider,
            AzureAIAgentClient(
                project_endpoint=project_endpoint,
                model_deployment_name=model_deployment,
                credential=credential,
            ) as client,
            ChatAgent(
                chat_client=client,
                name="search_agentic_probe",
                instructions=(
                    "You are a recruiter copilot with multi-hop reasoning skills. Use the search context to plan follow-up "
                    "queries, synthesize insights across documents, and state when the evidence is insufficient."
                ),
                context_providers=[search_provider],
            ) as agent,
        ):
            print("=== Azure AI Agent with Search Context (Agentic Mode) ===\n")

            for query in prompts:
                print(f"User: {query}")
                print("Agent: ", end="", flush=True)

                async for chunk in agent.run_stream(query):
                    if chunk.text:
                        print(chunk.text, end="", flush=True)

                print("\n")


async def main(argv: Iterable[str]) -> None:
    args = parse_args(argv)
    prompts: Sequence[str] = tuple(args.prompt) if args.prompt else DEFAULT_PROMPTS
    await run_agentic_demo(
        prompts,
        top_k=args.top_k,
        reasoning_effort=args.reasoning_effort,
        output_mode=args.output_mode,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
