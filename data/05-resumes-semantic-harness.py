#!/usr/bin/env python3
"""Semantic Azure AI Search harness for the resumes index.

Renamed from the Agent Framework sample `azure_ai_with_search_context_semantic.py`
so it matches our recruiting workflow files while preserving the documented
behavior from https://aka.ms/af/azureaisearch.
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
    "What information is available in the knowledge base?",
    "Summarize the main topics from the documents.",
    "Find specific details about the content.",
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
        description="Test Azure AI Search semantic mode using the Agent Framework sample harness.",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional prompts to run. Defaults to three sample questions when omitted.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=int(os.getenv("AZURE_SEARCH_TOP_K", "3")),
        help="Number of documents to retrieve per query (default: 3).",
    )
    return parser.parse_args(list(argv))


async def run_semantic_demo(prompts: Sequence[str], top_k: int) -> None:
    search_endpoint = _require_env("SEARCH_SERVICE_ENDPOINT", "AZURE_SEARCH_ENDPOINT")
    search_index = os.getenv("SEARCH_RESUME_INDEX") or os.getenv("AZURE_SEARCH_INDEX_NAME") or os.getenv("AZURE_SEARCH_INDEX")
    if not search_index:
        raise RuntimeError(
            "Set SEARCH_RESUME_INDEX (or legacy AZURE_SEARCH_INDEX_NAME/AZURE_SEARCH_INDEX) before running this harness."
        )

    project_endpoint = _require_env("FOUNDRY_PROJECT_ENDPOINT", "AZURE_AI_PROJECT_ENDPOINT")
    model_deployment = (
        os.getenv("FOUNDRY_MODEL_PRIMARY")
        or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        or "gpt-4o-mini"
    )
    semantic_config = os.getenv("AZURE_SEARCH_SEMANTIC_CONFIG") or "default"
    search_api_key = (
        os.getenv("SEARCH_SERVICE_API_KEY")
        or os.getenv("AZURE_SEARCH_API_KEY")
        or os.getenv("AZURE_SEARCH_KEY")
    )

    async with DefaultAzureCredential() as credential:
        search_provider = AzureAISearchContextProvider(
            endpoint=search_endpoint,
            index_name=search_index,
            api_key=search_api_key,
            credential=None if search_api_key else credential,
            mode="semantic",
            top_k=top_k,
            semantic_configuration_name=semantic_config,
        )

        async with (
            search_provider,
            AzureAIAgentClient(
                project_endpoint=project_endpoint,
                model_deployment_name=model_deployment,
                credential=credential,
            ) as client,
            ChatAgent(
                chat_client=client,
                name="search_semantic_probe",
                instructions=(
                    "You are a helpful recruiter assistant. Use ONLY the provided Azure AI Search context to answer. "
                    "When the context is insufficient, say so explicitly."
                ),
                context_providers=[search_provider],
            ) as agent,
        ):
            print("=== Azure AI Agent with Search Context (Semantic Mode) ===\n")

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
    await run_semantic_demo(prompts, top_k=args.top_k)


if __name__ == "__main__":
    try:
        asyncio.run(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
