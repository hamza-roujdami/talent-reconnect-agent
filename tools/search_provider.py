"""Azure AI Search context provider helpers."""

from __future__ import annotations

import os
from typing import Optional

from agent_framework.azure import AzureAISearchContextProvider
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

for env_file in (".env", ".env.local", ".emv"):
    load_dotenv(env_file, override=False)


class SearchConfigError(RuntimeError):
    """Raised when Azure AI Search configuration is incomplete."""


def _get_env(*names: str, required: bool = False, default: Optional[str] = None) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    if required:
        joined = " or ".join(names)
        raise SearchConfigError(f"Set {joined} in your environment.")
    return default


def _resolve_index_name() -> str:
    index = _get_env("SEARCH_RESUME_INDEX", "AZURE_SEARCH_INDEX_NAME", "AZURE_SEARCH_INDEX")
    if not index:
        raise SearchConfigError("Set SEARCH_RESUME_INDEX (or legacy AZURE_SEARCH_INDEX_NAME/AZURE_SEARCH_INDEX).")
    return index


def build_search_context_provider(
    *,
    mode: Optional[str] = None,
    top_k: Optional[int] = None,
    knowledge_base_name: Optional[str] = None,
) -> AzureAISearchContextProvider:
    """Create an AzureAISearchContextProvider configured from environment variables."""

    endpoint = _get_env("SEARCH_SERVICE_ENDPOINT", "AZURE_SEARCH_ENDPOINT", required=True)
    api_key = _get_env("SEARCH_SERVICE_API_KEY", "AZURE_SEARCH_API_KEY", "AZURE_SEARCH_KEY")
    resolved_mode = (mode or os.getenv("AZURE_SEARCH_MODE") or "semantic").lower()
    resolved_top_k = top_k or int(os.getenv("AZURE_SEARCH_TOP_K", "4"))
    semantic_config = os.getenv("AZURE_SEARCH_SEMANTIC_CONFIG") or "default"
    kb_output_mode = os.getenv("AZURE_SEARCH_KB_OUTPUT_MODE", "extractive_data")
    reasoning_effort = os.getenv("AZURE_SEARCH_RETRIEVAL_REASONING", "minimal")
    kb_name = knowledge_base_name or _get_env("SEARCH_KNOWLEDGE_BASE_NAME", "AZURE_SEARCH_KNOWLEDGE_BASE_NAME")

    credential = None if api_key else DefaultAzureCredential()

    kwargs: dict = {
        "endpoint": endpoint,
        "api_key": api_key,
        "credential": credential,
    }

    if resolved_mode == "agentic":
        kwargs.update(
            {
                "mode": "agentic",
                "knowledge_base_output_mode": kb_output_mode,
                "retrieval_reasoning_effort": reasoning_effort,
            }
        )

        if kb_name:
            kwargs["knowledge_base_name"] = kb_name
        else:
            index_name = _resolve_index_name()
            azure_openai_resource_url = _get_env(
                "FOUNDRY_CHAT_ENDPOINT",
                "AZURE_OPENAI_RESOURCE_URL",
                "AZURE_OPENAI_ENDPOINT",
            )
            if not azure_openai_resource_url:
                raise SearchConfigError(
                    "Set FOUNDRY_CHAT_ENDPOINT (or legacy AZURE_OPENAI_RESOURCE_URL/AZURE_OPENAI_ENDPOINT) when using agentic search over an index."
                )
            model_deployment = _get_env(
                "FOUNDRY_MODEL_FAST",
                "FOUNDRY_MODEL_PRIMARY",
                "AZURE_OPENAI_AGENTIC_DEPLOYMENT",
                "AZURE_AI_MODEL_DEPLOYMENT_NAME",
                "AZURE_OPENAI_DEPLOYMENT",
                default="gpt-4o-mini",
            )
            kwargs.update(
                {
                    "index_name": index_name,
                    "azure_openai_resource_url": azure_openai_resource_url,
                    "model_deployment_name": model_deployment,
                    "top_k": resolved_top_k,
                }
            )
    else:
        kwargs.update(
            {
                "mode": "semantic",
                "index_name": _resolve_index_name(),
                "top_k": resolved_top_k,
                "semantic_configuration_name": semantic_config,
            }
        )

    return AzureAISearchContextProvider(**kwargs)
