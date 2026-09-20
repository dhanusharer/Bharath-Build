# ADR-007: Provider Abstraction for Text-to-Speech (TTS)

## Status
Accepted (Phase 0 Freeze)

## Context
The application targets voice accessibility in Indian regional languages, specifically Hindi and Kannada.
* Amazon Polly provides excellent Neural voices for Hindi (`Kajal`).
* However, Amazon Polly does not currently support native Neural voices for Kannada (`kn-IN`).
* Direct coupling of application business logic or route handlers to the `boto3.client('polly')` SDK would prevent supporting Kannada, prevent testing with offline mock engines, and lock the system to a single vendor.

## Decision
We define an abstract interface port: **`ITTSProvider` with dynamic language routing**.
* The domain and application use cases interact strictly with `ITTSProvider.synthesize(text, language_code)`.
* A `TTSProviderFactory` inspects the requested `language_code` and environment configuration:
  * For `hi-IN`: Routes to `PollyTTSAdapter` using voice `Kajal`.
  * For `kn-IN`: Routes to a dedicated regional TTS provider adapter (e.g. specialized regional engine or `MockTTSAdapter` for local CI/development).
  * For local unit testing: Routes to `MockTTSAdapter` returning synthetic sine-wave audio bytes without incurring cloud network calls or costs.

## Alternatives Considered
1. **Hardcoding Amazon Polly for all languages**: Would completely exclude Kannada from voice synthesis, failing a primary product objective.
2. **External Voice-as-a-Service SaaS directly in React Frontend**: Moves vendor credentials to the client browser, introduces security risks, and bypasses backend audit logging of spoken medical advice.

## Consequences
* **Positive**: Full multi-language adaptability; decoupled vendor dependencies; zero AWS costs during local testing; clean substitution when Polly releases Kannada Neural voices.
* **Negative**: Introduces adapter maintenance overhead and necessitates managing audio stream conversions across heterogeneous vendor formats.
