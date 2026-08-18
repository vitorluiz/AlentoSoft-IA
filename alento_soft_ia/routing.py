"""Roteamento seguro entre modelos locais e providers cloud."""

from __future__ import annotations

import os
from typing import Any, Dict

from .provider import OllamaProvider, OpenAICompatibleProvider


CLOUD_PROVIDERS = {"openai", "openrouter"}
CLOUD_ALLOWED_DOMAINS = {"marketing"}
DEFAULT_MARKETING_SOURCES = {
    "granjimmy_contexto_marca.md",
    "granjimmy_contexto_minimo.md",
}


def _source_allowlist() -> set[str]:
    configured = os.getenv("ALENTO_CLOUD_MARKETING_SOURCES", "").strip()
    if configured:
        return {item.strip() for item in configured.split(",") if item.strip()}
    return set(DEFAULT_MARKETING_SOURCES)


def _cloud_marketing_is_allowed(domain: str, context: Dict[str, Any]) -> bool:
    """Permite somente fontes explicitamente registradas como públicas/autorizadas."""
    if domain not in CLOUD_ALLOWED_DOMAINS:
        return False
    source_name = str(context.get("source_name", "")).strip()
    source_text = str(context.get("source_text", "")).strip()
    return bool(source_text and source_name in _source_allowlist())


def _require_cloud_marketing(domain: str, context: Dict[str, Any]) -> None:
    if domain not in CLOUD_ALLOWED_DOMAINS:
        raise RuntimeError(
            "Roteamento cloud bloqueado: somente o domínio marketing pode usar provider externo. "
            "Prontuários, clínica, RH e financeiro devem usar Ollama local."
        )
    if not _cloud_marketing_is_allowed(domain, context):
        allowed = ", ".join(sorted(_source_allowlist()))
        raise RuntimeError(
            "Roteamento cloud bloqueado: a fonte de marketing não está na lista autorizada. "
            f"Fontes permitidas: {allowed}."
        )


def _build_openai(model: str | None = None) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name="openai",
        base_url=os.getenv(
            "OPENAI_BASE_URL",
            os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
        ),
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=model or os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        require_api_key=True,
    )


def _build_openrouter(model: str | None = None) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name="openrouter",
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
        model=model or os.getenv("OPENROUTER_MODEL", ""),
        headers={
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://github.com/vitorluiz/AlentoSoft-IA"),
            "X-OpenRouter-Title": "AlentoSoft-IA",
        },
        require_api_key=True,
    )


def build_provider(
    provider_name: str,
    domain: str,
    context: Dict[str, Any],
    model: str | None = None,
):
    """Seleciona o provider e aplica a barreira de domínio antes da geração.

    `hybrid` usa cloud somente para marketing com fonte allowlisted. Para todos os
    outros domínios, inclusive clinical, retorna Ollama sem fazer chamada externa.
    """
    if provider_name == "ollama":
        return OllamaProvider(model=model)

    if provider_name in CLOUD_PROVIDERS:
        _require_cloud_marketing(domain, context)
        return _build_openai(model) if provider_name == "openai" else _build_openrouter(model)

    if provider_name == "hybrid":
        if _cloud_marketing_is_allowed(domain, context):
            selected = os.getenv("ALENTO_CLOUD_PROVIDER", "openrouter").strip().lower()
            if selected not in CLOUD_PROVIDERS:
                raise RuntimeError(
                    "ALENTO_CLOUD_PROVIDER deve ser 'openai' ou 'openrouter' quando hybrid usar cloud."
                )
            return _build_openai(model) if selected == "openai" else _build_openrouter(model)
        return OllamaProvider(model=model)

    raise ValueError(f"Provider desconhecido: {provider_name}")


__all__ = ["build_provider", "CLOUD_ALLOWED_DOMAINS", "DEFAULT_MARKETING_SOURCES"]
