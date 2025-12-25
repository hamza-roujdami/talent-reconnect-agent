#!/usr/bin/env python3
"""Agentic Azure AI Search harness for the interview-feedback index."""

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
    "Compare the interview history for candidates 1, 2, and 3.",
    "Who moved from no-hire to hire recommendations over time?",
    "Summarize red flags that appear across multiple interviewers.",
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
        description="Exercise Azure AI Search agentic mode against the interview-feedback knowledge base.",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional prompts to run. Defaults to recruiter-focused samples when omitted.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=int(os.getenv("AZURE_FEEDBACK_TOP_K", os.getenv("AZURE_SEARCH_TOP_K", "4"))),
        help="Number of documents to retrieve per hop when issuing index queries (default: 4).",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=("minimal", "low", "medium"),
        default=os.getenv("AZURE_FEEDBACK_RETRIEVAL_REASONING", os.getenv("AZURE_SEARCH_RETRIEVAL_REASONING", "minimal")),
        help="Adjust agentic retrieval reasoning effort (default: minimal).",
    )
    parser.add_argument(
        "--output-mode",
        choices=("extractive_data", "answer_synthesis"),
        default=os.getenv("AZURE_FEEDBACK_KB_OUTPUT_MODE", os.getenv("AZURE_SEARCH_KB_OUTPUT_MODE", "extractive_data")),
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

    feedback_kb_name = (
        os.getenv("SEARCH_FEEDBACK_KNOWLEDGE_BASE_NAME")
        or os.getenv("AZURE_FEEDBACK_KNOWLEDGE_BASE_NAME")
        or os.getenv("AZURE_SEARCH_KNOWLEDGE_BASE_NAME")
    )

    provider_kwargs = {
        "endpoint": search_endpoint,
        "mode": "agentic",
        "knowledge_base_output_mode": output_mode,
        "retrieval_reasoning_effort": reasoning_effort,
        "api_key": search_api_key,
    }

    if feedback_kb_name:
        provider_kwargs["knowledge_base_name"] = feedback_kb_name
    else:
        feedback_index = _resolve_feedback_index()
        azure_openai_resource_url = (
            os.getenv("FOUNDRY_CHAT_ENDPOINT")
            or os.getenv("AZURE_OPENAI_RESOURCE_URL")
            or os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        if not azure_openai_resource_url:
            raise RuntimeError(
                "Set FOUNDRY_CHAT_ENDPOINT (or legacy AZURE_OPENAI_RESOURCE_URL/AZURE_OPENAI_ENDPOINT) when using agentic mode over an index."
            )
        provider_kwargs.update(
            {
                "index_name": feedback_index,
                "azure_openai_resource_url": azure_openai_resource_url,
                "model_deployment_name": model_deployment,
                "top_k": top_k,
            }
        )

    async with DefaultAzureCredential() as credential:
        provider_kwargs["credential"] = None if search_api_key else credential

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
                name="feedback_agentic_probe",
                instructions=(
                    "You reason across interview feedback to spot cross-candidate signals, summarize interviewer "
                    "sentiment, and warn about recurring red flags. Rely only on the retrieved context."
                ),
                context_providers=[search_provider],
            ) as agent,
        ):
            print("=== Azure AI Agent with Search Context (Feedback · Agentic Mode) ===\n")

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
