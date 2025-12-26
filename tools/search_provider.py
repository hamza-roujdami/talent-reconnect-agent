"""Azure AI Search context provider helpers."""

from __future__ import annotations

import os
from typing import Any, Optional, MutableSequence

from agent_framework import ChatMessage, Context, Role
from agent_framework.azure import AzureAISearchContextProvider
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
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
    if os.getenv("AZURE_SEARCH_REQUIRE_AGENTIC", "").lower() == "true" and resolved_mode != "agentic":
        raise SearchConfigError("AZURE_SEARCH_REQUIRE_AGENTIC is set but resolved mode is not agentic.")
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


# ---------------------------------------------------------------------------
# Custom semantic search provider that explicitly includes `id` and `email`
# ---------------------------------------------------------------------------

from agent_framework import ContextProvider


class ResumeSearchContextProvider(ContextProvider):
    """Semantic search context provider that ensures `id` and `email` fields appear in context."""

    _CONTEXT_PROMPT = "Use the following resumes as context. Each resume includes id, email, name, and other details."

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: Optional[str] = None,
        index_name: str,
        top_k: int = 5,
        semantic_configuration_name: str = "default",
    ):
        self._endpoint = endpoint
        self._api_key = api_key
        self._index_name = index_name
        self._top_k = top_k
        self._semantic_config = semantic_configuration_name

        cred = AzureKeyCredential(api_key) if api_key else DefaultAzureCredential()
        self._client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=cred,
        )

    def close(self) -> None:
        """Close underlying HTTP client to avoid unclosed session warnings."""
        try:
            self._client.close()
        except Exception:
            pass

    def __del__(self) -> None:
        self.close()

    async def invoking(
        self,
        messages: ChatMessage | MutableSequence[ChatMessage],
        **kwargs: Any,
    ) -> Context:
        msgs = [messages] if isinstance(messages, ChatMessage) else list(messages)
        user_texts = [m.text for m in msgs if m.text and m.role == Role.USER]
        query = " ".join(user_texts) if user_texts else ""
        if not query.strip():
            return Context()

        # Semantic hybrid search
        from azure.search.documents.models import QueryType

        results = self._client.search(
            search_text=query,
            top=self._top_k,
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name=self._semantic_config,
        )

        formatted: list[str] = []
        for doc in results:
            doc_id = doc.get("id", "unknown")
            email = doc.get("email", "")
            name = doc.get("name", "")
            title = doc.get("current_title", "")
            company = doc.get("current_company", "")
            location = doc.get("location", "")
            exp = doc.get("experience_years", "")
            skills = ", ".join(doc.get("skills", [])[:10])
            summary = doc.get("summary", "")
            education = doc.get("education", "")
            certs = ", ".join(doc.get("certifications", [])[:3])

            text = (
                f"[Source: {doc_id}]\n"
                f"id: {doc_id}\n"
                f"email: {email}\n"
                f"name: {name}\n"
                f"title: {title}\n"
                f"company: {company}\n"
                f"location: {location}\n"
                f"experience_years: {exp}\n"
                f"skills: {skills}\n"
                f"summary: {summary}\n"
                f"education: {education}\n"
                f"certifications: {certs}"
            )
            formatted.append(text)

        if not formatted:
            return Context()

        context_msgs = [ChatMessage(role=Role.USER, text=self._CONTEXT_PROMPT)]
        context_msgs.extend([ChatMessage(role=Role.USER, text=part) for part in formatted])
        return Context(messages=context_msgs)


def build_resume_search_provider(*, top_k: Optional[int] = None) -> ResumeSearchContextProvider:
    """Build a ResumeSearchContextProvider with explicit id/email formatting."""

    endpoint = _get_env("SEARCH_SERVICE_ENDPOINT", "AZURE_SEARCH_ENDPOINT", required=True)
    api_key = _get_env("SEARCH_SERVICE_API_KEY", "AZURE_SEARCH_API_KEY", "AZURE_SEARCH_KEY")
    index_name = _resolve_index_name()
    resolved_top_k = top_k or int(os.getenv("AZURE_SEARCH_TOP_K", "5"))
    semantic_config = os.getenv("AZURE_SEARCH_SEMANTIC_CONFIG") or "default"

    return ResumeSearchContextProvider(
        endpoint=endpoint,
        api_key=api_key,
        index_name=index_name,
        top_k=resolved_top_k,
        semantic_configuration_name=semantic_config,
    )


# ---------------------------------------------------------------------------
# Hybrid agentic provider: agentic reasoning + real document fields
# ---------------------------------------------------------------------------


class HybridAgenticSearchProvider(ContextProvider):
    """
    Hybrid provider that combines agentic search quality with accurate field extraction.
    
    1. Runs agentic KB search for intelligent relevance ranking and summaries
    2. Runs parallel semantic search to get real document IDs and emails
    3. Returns both: agentic context + structured candidate data with real fields
    """

    _FIELD_DATA_PROMPT = """
IMPORTANT: The following is the AUTHORITATIVE list of candidate documents with their REAL IDs and emails.
When presenting candidates, you MUST use these exact IDs and emails - do not synthesize or guess values.
"""

    def __init__(
        self,
        *,
        agentic_provider: AzureAISearchContextProvider,
        endpoint: str,
        api_key: Optional[str] = None,
        index_name: str,
        top_k: int = 10,
        semantic_configuration_name: str = "default",
    ):
        self._agentic = agentic_provider
        self._endpoint = endpoint
        self._api_key = api_key
        self._index_name = index_name
        self._top_k = top_k
        self._semantic_config = semantic_configuration_name

        cred = AzureKeyCredential(api_key) if api_key else DefaultAzureCredential()
        self._client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=cred,
        )

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    def __del__(self) -> None:
        self.close()

    async def invoking(
        self,
        messages: ChatMessage | MutableSequence[ChatMessage],
        **kwargs: Any,
    ) -> Context:
        # Run agentic search first
        agentic_context = await self._agentic.invoking(messages, **kwargs)

        # Extract query from messages
        msgs = [messages] if isinstance(messages, ChatMessage) else list(messages)
        user_texts = [m.text for m in msgs if m.text and m.role == Role.USER]
        query = " ".join(user_texts) if user_texts else ""
        if not query.strip():
            return agentic_context

        # Run semantic search to get real document fields
        from azure.search.documents.models import QueryType

        results = self._client.search(
            search_text=query,
            top=self._top_k,
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name=self._semantic_config,
        )

        # Build structured field data
        field_lines = ["REAL CANDIDATE DATA (use these exact values):"]
        for i, doc in enumerate(results, 1):
            doc_id = doc.get("id", "unknown")
            email = doc.get("email", "")
            name = doc.get("name", "")
            title = doc.get("current_title", "")
            company = doc.get("current_company", "")
            location = doc.get("location", "")
            exp = doc.get("experience_years", "")
            skills = ", ".join(doc.get("skills", [])[:8])

            field_lines.append(
                f"#{i}: id={doc_id} | email={email} | name={name} | "
                f"title={title} | company={company} | location={location} | "
                f"exp={exp}yrs | skills={skills}"
            )

        if len(field_lines) <= 1:
            return agentic_context

        # Combine: agentic context + field data instruction
        combined_msgs = list(agentic_context.messages) if agentic_context.messages else []
        combined_msgs.append(ChatMessage(role=Role.USER, text=self._FIELD_DATA_PROMPT))
        combined_msgs.append(ChatMessage(role=Role.USER, text="\n".join(field_lines)))

        return Context(messages=combined_msgs)


def build_hybrid_agentic_provider(*, top_k: Optional[int] = None) -> HybridAgenticSearchProvider:
    """Build a hybrid provider: agentic reasoning + real document fields."""

    endpoint = _get_env("SEARCH_SERVICE_ENDPOINT", "AZURE_SEARCH_ENDPOINT", required=True)
    api_key = _get_env("SEARCH_SERVICE_API_KEY", "AZURE_SEARCH_API_KEY", "AZURE_SEARCH_KEY")
    index_name = _resolve_index_name()
    resolved_top_k = top_k or int(os.getenv("AZURE_SEARCH_TOP_K", "10"))
    semantic_config = os.getenv("AZURE_SEARCH_SEMANTIC_CONFIG") or "default"

    # Build the underlying agentic provider
    agentic_provider = build_search_context_provider(mode="agentic", top_k=resolved_top_k)

    return HybridAgenticSearchProvider(
        agentic_provider=agentic_provider,
        endpoint=endpoint,
        api_key=api_key,
        index_name=index_name,
        top_k=resolved_top_k,
        semantic_configuration_name=semantic_config,
    )
