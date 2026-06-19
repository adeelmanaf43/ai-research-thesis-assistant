# Provider Architecture

The provider layer is designed to keep the product local-first while allowing optional AI providers later. The app must remain useful when Ollama is not installed, a model is unavailable, hardware is weak, or no paid API key exists.

## Core Principle

Local processing is the foundation. Provider integrations are optional enhancements, not requirements.

Current default behavior:

```text
PROVIDER_MODE=local
  -> provider factory selects LocalLLMProvider
  -> local summaries, research extraction, search, and Q&A stay available
  -> no network, paid API, or Ollama server is required
```

Future optional behavior:

```text
PROVIDER_MODE=ollama
  -> provider factory recognizes the requested mode
  -> current milestone falls back to local
  -> later milestones can plug in Ollama behind the same interface
```

## Files

- `backend/app/services/llm/base.py`: abstract provider contract and shared response dataclasses.
- `backend/app/services/llm/local_provider.py`: local provider implementation with no external model calls.
- `backend/app/services/llm/factory.py`: provider selection based on configuration.
- `backend/tests/test_llm_base.py`: interface and response contract tests.
- `backend/tests/test_llm_factory.py`: provider selection and fallback tests.
- `backend/tests/test_local_provider.py`: local provider behavior tests.

## Base Provider Contract

`BaseLLMProvider` defines four required methods:

- `generate_summary(text, max_words=150)`
- `answer_question(question, context_chunks, max_answer_sentences=3)`
- `extract_research_info(text, sections=None)`
- `health_check()`

Every concrete provider must implement these methods. This prevents routes from depending on provider-specific details and makes future Ollama or cloud providers easier to test.

## Shared Response Types

Provider responses use explicit dataclasses:

- `ProviderResponse`: content, provider name, optional model, source chunks, metadata, limitations, and fallback flag.
- `ProviderHealth`: provider name, availability, message, and diagnostic details.
- `ProviderSelection`: requested mode, resolved mode, selected provider, fallback flag, and selection message.

These response objects make provider behavior visible instead of hiding failures behind generic strings.

## Local Provider

`LocalLLMProvider` implements the provider interface without calling an external model.

It uses existing local services:

- Extractive sentence scoring for summaries.
- Retrieved chunks for source-grounded Q&A.
- Rule-based research information extraction.
- Always-available health check because no network service is required.

The older function-based local Q&A remains available so existing routes continue to work while provider orchestration evolves.

## Factory Behavior

The factory accepts a configured provider mode and returns a provider selection:

| Requested mode | Resolved provider | Behavior |
| --- | --- | --- |
| `local` | `LocalLLMProvider` | Default local-first behavior. |
| `ollama` | `LocalLLMProvider` | Recognized future mode; currently falls back to local. |
| unknown value | none | Raises `ProviderConfigurationError`. |

This behavior avoids fake Ollama support. The system can acknowledge `ollama` as a planned optional mode without pretending it is implemented.

## Failure Policy

Provider failures should not break core document intelligence.

Rules for future providers:

- Do not send full documents, full chapters, or unlimited context to a model.
- Use only bounded summaries, selected sections, or top retrieved chunks.
- Apply timeouts and exception handling around model calls.
- Return a clear fallback response when the provider is unavailable.
- Preserve local answers and local analysis when optional providers fail.
- Never require paid API keys for the MVP.
- Never hardcode secrets.

## Why This Matters

This architecture separates document intelligence from model availability. The project can be demonstrated and tested on any local machine, then improved with optional Ollama later without rewriting routes or services.

Interview-ready summary:

```text
I designed the provider layer as an optional boundary. The local provider implements the same interface as future model providers, and the factory chooses the provider from configuration. Ollama is recognized but currently falls back to local, so the app does not break when no model server exists. This keeps the system honest, testable, and local-first.
```
