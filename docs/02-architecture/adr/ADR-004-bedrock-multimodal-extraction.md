# ADR-004: Amazon Bedrock Multimodal Foundation Models for Extraction

## Status
Accepted (Phase 0 Freeze)

## Context
Deciphering handwritten medical prescriptions requires advanced multimodal vision-language understanding. Indian prescriptions feature idiosyncratic cursive scripts, inconsistent abbreviations, orientation skews, and mixed tabular layouts. Traditional OCR systems (e.g. Tesseract, AWS Textract) produce disjointed character fragments and struggle with cursive medical handwriting.

## Decision
We select **Amazon Bedrock using Anthropic Claude 3.5 Sonnet (`anthropic.claude-3-5-sonnet-20241022-v2:0`)** for multimodal prescription extraction.
* Claude 3.5 Sonnet offers top-tier spatial and cursive handwriting comprehension and strong adherence to structured output schemas.
* Amazon Bedrock provides fully managed, serverless invocation in the Mumbai region (`ap-south-1`) with zero data retention for training on inference payloads.
* Temperature is fixed at `0.0` to maximize deterministic token recognition and minimize creative variance.

## Alternatives Considered
1. **Amazon Textract**: Efficient for standardized printed forms, but repeatedly demonstrated poor accuracy on unstructured cursive Indian physician handwriting.
2. **OpenAI GPT-4o via External API**: Exceptional multimodal capability, but data leaves the AWS ecosystem and lacks local Indian data sovereignty guarantees compared to Bedrock in `ap-south-1`.
3. **Self-Hosted Open-Source Vision Model (Llama-Vision 11B / Qwen2-VL)**: Requires costly dedicated GPU instances (EC2 g5.xlarge) with complex scaling and cold-start latencies.

## Consequences
* **Positive**: High fidelity on difficult cursive tokens; enterprise compliance via Bedrock; zero GPU infrastructure management.
* **Negative**: API inference latency typically ranges from 2.5s to 5.5s; ongoing token costs require careful payload budgeting; vendor API throttling limits require client-side circuit breakers.
