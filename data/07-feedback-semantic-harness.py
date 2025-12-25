#!/usr/bin/env python3
"""Semantic Azure AI Search harness for the feedback index."""

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

for env_file in (".env", ".env.local", ".emv"):
    load_dotenv(env_file, override=False)

DEFAULT_PROMPTS: Sequence[str] = (
    "What historical interview signals should I know about for the current shortlist?",
    "List the strongest hire recommendations logged in the feedback knowledge base.",
    "Which candidates were flagged with no-hire decisions in the past quarter?",
)


def _require_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    joined = " or ".join(names)
    raise RuntimeError(f"Environment variable {joined} is required for this harness.")


def _resolve_feedback_index() -> str:
    index = os.getenv("SEARCH_FEEDBACK_INDEX") or os.getenv("AZURE_FEEDBACK_INDEX_NAME") or os.getenv("AZURE_FEEDBACK_INDEX")
    if not index:
        raise RuntimeError(
            "Set SEARCH_FEEDBACK_INDEX (or legacy AZURE_FEEDBACK_INDEX_NAME/AZURE_FEEDBACK_INDEX) before running this harness."
        )
    return index


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test Azure AI Search semantic mode against the interview-feedback index.",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional prompts to run. Defaults to recruiter-focused samples when omitted.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=int(os.getenv("AZURE_FEEDBACK_TOP_K", os.getenv("AZURE_SEARCH_TOP_K", "3"))),
        help="Number of feedback documents to retrieve per query (default: 3).",
    )
    return parser.parse_args(list(argv))


async def run_semantic_demo(prompts: Sequence[str], top_k: int) -> None:
    search_endpoint = _require_env("SEARCH_SERVICE_ENDPOINT", "AZURE_SEARCH_ENDPOINT")
    feedback_index = _resolve_feedback_index()
    project_endpoint = _require_env("FOUNDRY_PROJECT_ENDPOINT", "AZURE_AI_PROJECT_ENDPOINT")
    model_deployment = (
        os.getenv("FOUNDRY_MODEL_FAST")
        or os.getenv("FOUNDRY_MODEL_PRIMARY")
        or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        or "gpt-4o-mini"
    )
    semantic_config = (
        os.getenv("SEARCH_FEEDBACK_SEMANTIC_CONFIG")
        or os.getenv("AZURE_FEEDBACK_SEMANTIC_CONFIG")
        or os.getenv("AZURE_SEARCH_SEMANTIC_CONFIG")
        or "feedback-semantic"
    )
    search_api_key = (
        os.getenv("SEARCH_SERVICE_API_KEY")
        or os.getenv("AZURE_SEARCH_API_KEY")
        or os.getenv("AZURE_SEARCH_KEY")
    )

    async with DefaultAzureCredential() as credential:
        search_provider = AzureAISearchContextProvider(
            endpoint=search_endpoint,
            index_name=feedback_index,
            mode="semantic",
            top_k=top_k,
            semantic_configuration_name=semantic_config,
            api_key=search_api_key,
            credential=None if search_api_key else credential,
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
                name="feedback_semantic_probe",
                instructions=(
                    "You analyze interview feedback stored in Azure AI Search. Cite the retrieved notes and "
                    "call out red flags explicitly. If the knowledge base does not contain an answer, say so."
                ),
                context_providers=[search_provider],
            ) as agent,
        ):
            print("=== Azure AI Agent with Search Context (Feedback · Semantic Mode) ===\n")

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
