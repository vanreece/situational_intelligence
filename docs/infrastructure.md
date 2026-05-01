# Infrastructure

Compute resources available to this project.

## Homelab

### Qwen3-Coder-30B-A3B-Instruct (4-bit GPTQ)

- **Endpoint:** `http://192.168.100.101:8080` (OpenAI-compatible, vLLM-backed)
- **Model id for API requests:** `btbtyler09/Qwen3-Coder-30B-A3B-Instruct-gptq-4bit`
- **Shape:** Qwen3 MoE — 30B total params, ~3B active per token (the "A3B" suffix). Instruct-tuned for code, 4-bit GPTQ.
- **Context window:** 32,768 tokens.
- **Capabilities exposed:** sampling and logprobs. Logprobs are load-bearing for calibration — they let us turn binary classifier outputs into probability distributions that calibrate cleanly against held-out ground truth. Use them.
- **Cost characteristics:** High throughput, high concurrency, free at the margin.
- **Architectural slot:** Primary candidate for the **cheap classification tier** (Layer 2 in `architecture.md`). Strong fit for binary classifiers and tight-schema extraction at volume. Also viable for bulk discovery-mode "matched nothing" sampling at volumes that would be uneconomic against frontier-tier APIs.
- **Not suited for:** Synthesis-layer work that requires holding many sources in context and reasoning across them — that's frontier-tier work. The cost-tier hierarchy still applies.
- **Empirical questions worth settling early:**
  - **Coder-tuning bias.** How much does the code-tuning cost us on general-text classification (mailing-list register, GAO PDFs, ASRS narratives)? A/B against a frontier-tier baseline on the same items.
  - **U3 is partially this model class.** "How small can the cheap classification tier get without losing accuracy?" — treat the homelab model not just as production substrate but as a primary *subject* of measurement. Where it cliffs against frontier baselines is part of the answer to U3.
  - **Throughput envelope.** What concurrency does it actually sustain before tail latency degrades? Affects whether harvest-time classification is feasible.

## API access (frontier tier)

To be filled in as we wire up Anthropic / other API access for synthesis-layer and discovery-mode work.
