# AI Detection Landscape Reference

**Version**: 1.0
**Effective**: 2026-04-18
**Applies to**: `ai-detection-agent` pipeline audits and detection scoring interpretation

> Background reference for the `ai-detection-agent`. Read this file at the start of any
> Mode 2 audit. Snapshot date: 2026-04-01. Update quarterly or when a major detector
> version ships.

---

## Detection Architecture Overview

As of April 2026, the detection landscape has shifted away from heuristic classifiers that
rely on static perplexity and burstiness metrics. The ecosystem is now dominated by three
architectural families:

1. **Continuous-state editing quantifiers** (Pangram EditLens): treat detection as regression,
   not binary classification. Measure the extent of AI editing rather than a pass/fail label.
2. **Retrieval-augmented provenance matching** (Copyleaks AI Source Match): cross-reference
   submitted text against a corpus of confirmed AI outputs to isolate generation traces.
3. **Zero-shot probability curvature analysis** (Binoculars, Fast-DetectGPT): exploit the
   statistical property that AI-generated text sits in local probability maxima without
   requiring fine-tuning on labeled data.

Legacy tools relying on perplexity thresholds and simple burstiness scoring (ZeroGPT,
Scribbr, early Turnitin) have largely been discredited in enterprise and academic settings.

---

## Detector Profiles

### Pangram (v3.2) — Primary Scoring Engine

**Architecture**: EditLens continuous regression. Uses lightweight similarity metrics as
intermediate supervision to estimate the precise, continuous extent of AI editing.

**Key metrics**:
- 94.7% F1 on binary classification
- 90.4% F1 on ternary (Human / AI / Mixed)
- 0.5% false positive rate on clean text
- Near-zero error on unedited human distributions

**Blind spots**: Susceptible to extreme adversarial paraphrasing that fully dismantles
syntactic structure. Excels at catching lightly edited or "humanized" text that defeats
legacy detectors.

**Model coverage**: GPT-4o/5, Claude 4.5, Gemini 2.5.

**Version notes**: v3.2 launched early 2026. Incrementally improved recall (true positive
rate) over v3.1.

---

### Binoculars — Self-Hosted (P40)

**Architecture**: Zero-shot detection via contrastive log-probabilities between two distinct
LLMs (scorer model and observer model, typically Falcon-7B variants).

**Key metrics**:
- AUROC > 0.99 on standard clean benchmarks without domain-specific fine-tuning
- Materially outperforms Ghostbuster in out-of-domain settings
- No API key required; runs entirely on local GPU

**Blind spots**: Vulnerable to StealthRL-class reinforcement learning paraphrase attacks
that drop AUROC toward random chance (mean TPR of 0.024 at 1% FPR under GRPO adversarial
conditions).

**Deployment**: Docker container on P40 (24GB VRAM; both 7B models fit simultaneously in
FP16 at ~14GB). Exposed as a REST API at `http://binoculars:8421/score`.

---

### Fast-DetectGPT — Self-Hosted (P40)

**Architecture**: Zero-shot detection via conditional probability curvature analysis.
Measures how the probability of a text sequence changes under slight perturbations,
exploiting the property that AI text resides in local probability maxima.

**Key metrics**: Strong AUROC on clean benchmarks; academic gold standard for zero-shot
detection alongside Binoculars.

**Deployment**: Co-hosted in the Docker service alongside Binoculars on the P40.

---

### Sapling — Public API

**Architecture**: Real-time transformer token probability estimation, per-sentence
granularity.

**Key metrics**: Claims 97% accuracy; specializes in multilingual and live enterprise
API workflows.

**Value**: Per-sentence scores pinpoint exactly which sentences to revise, not just
which paragraphs. Useful as a targeted revision tool after Pangram identifies a high-risk
section.

**API**: `api.sapling.ai`

---

### Winston AI — Public API

**Architecture**: Ensemble classifier with optical character recognition support and
weekly algorithmic updates.

**Key metrics**: ~95% accuracy on academic-style writing.

**API**: `api.gowinston.ai`

---

### Turnitin AI Writing Indicator (Clarity)

**Architecture**: Transformer-based stylometric ensembles for long-form prose.

**Key metrics**: Claims up to 98% accuracy. Implemented a hard confidence suppression
threshold in 2026: all AI scores below 20% are suppressed and marked with an asterisk
to prevent unwarranted disciplinary actions.

**Blind spots**: Minimum 300 words of prose required; struggles with documents heavy in
code blocks or non-standard formatting.

**Access**: Institutional only. No public API.

---

### Originality.ai (Turbo 3.0)

**Architecture**: Aggressive fine-tuned neural classification targeting deep perplexity
and burstiness. Designed for web publishers and SEO professionals.

**Key metrics**: 96-98% accuracy; 2% FPR on clean benchmarks. Highest commercial
resilience against paraphrased and humanized text.

**Critical caveat**: Elevated false positives on highly structured, technical, or
constrained human writing (legal abstracts, compliance drafts). Originality.ai interprets
low-entropy domain writing as machine-generated.

**Access**: Enterprise API only as of 2026.

---

### GPTZero

**Architecture**: Deep document parsing on perplexity and burstiness with a "Mixed
Classification" tier for sentence-by-sentence variance.

**Key metrics**: Vendor claims 99.3% accuracy with 0.24% FPR. Independent benchmarks
place real-world accuracy at 84-90% on hybrid documents; FPR of 6-10% depending on
domain.

**Blind spots**: Struggles with short text (under 150 words) and non-native English.

**Access**: Enterprise API only as of 2026.

---

### Copyleaks

**Architecture**: Multilingual NLP classification plus "AI Source Match" retrieval.
AI Source Match cross-references submitted text against a corpus of confirmed AI outputs
to isolate the original generation source by exploiting LLM structural repetition.

**Key metrics**: 94% accuracy; 4% FPR.

**Critical relevance**: AI Source Match directly exploits fixed MCP prompt templates.
Identical cookiecutter structures submitted repeatedly create a self-plagiarism loop
that retrieval-based detection identifies immediately.

**Access**: Enterprise API only as of 2026.

---

### ZeroGPT — Do Not Benchmark Against

**Architecture**: Outdated perplexity heuristics.

**Key metrics**: Claims 98.8% accuracy; independent 2026 evaluations show 70-85%
real-world accuracy with FPR as high as 33%. Trivially bypassed by commercial humanizers.

**Verdict**: Discredited in institutional and enterprise settings. Optimizing for ZeroGPT
provides a false sense of security and no protection against modern ensemble architectures.

---

### Academic Open-Source Detectors

**Ghostbuster**: Structured search using weaker language models (unigram, trigram,
non-instruction GPT-3) to compute generation probabilities. Achieves 99.0 F1 historically;
generalizes well across unseen models.

**MAGE**: Robust sequence modeling for machine-generated text detection. Vulnerable to
StealthRL RL paraphrase attacks as of early 2026 benchmarks.

**RAID Benchmark**: 10 million documents across 11 LLMs and 12 adversarial attacks.
Ensemble architectures (RoBERTa + XLM-R + BERT variants) maintain > 99% accuracy at 5%
FPR even against StealthRL.

---

## Empirical Scoring Matrix (Proxy Evaluation, 2026-04-01)

Scores are synthesized proxy evaluations based on documented detector behavior profiles.
Not live API results.

| Sample | Domain / Origin | Pangram | Originality | GPTZero | Turnitin | Copyleaks |
|--------|----------------|---------|-------------|---------|----------|-----------|
| Human Tech | Python auth docs (pre-AI) | 0.8% | 45% (FP) | 12% | <20%* | 15% |
| Human Legal | Oregon legal standard (pre-AI) | 1.2% | 68% (FP) | 18% | <20%* | 22% |
| System-edited | Security audit (MCP output) | 85.0% | 92% | 55% (Mixed) | 48% | 88% |
| System-edited | TDD execution plan (MCP) | 78.5% | 88% | 42% (Mixed) | 35% | 72% |
| Unedited AI | Zero Trust (raw zero-shot) | 99.8% | 100% | 99% | 98% | 99% |
| Hybrid | RAG-processor API docs | 62.4% | 85% | 65% (Mixed) | 55% | 60% |

*Turnitin suppresses scores below 20%, denoted with asterisk.

**Key findings:**
- Pangram correctly scores constrained human legal writing at < 2% (low FPR due to EditLens
  regression architecture).
- Originality.ai produces false positives at 45-68% on pre-AI human writing in technical and
  legal domains.
- System-edited MCP outputs score 78-85% on Pangram; these are the primary revision targets.
- ZeroGPT is bypassed entirely by the system's prompt-time constraints (12-15% on edited output).

---

## Reference Library Vulnerability Analysis

### What the current system defeats

| Mechanism | Defeated Tools |
|-----------|---------------|
| Lexical constraints (Oregon legal style) | ZeroGPT, Scribbr, basic N-gram matchers |
| Syntactic TDD workflows | Scribbr, Turnitin (partial, via 20% suppression floor) |
| Burstiness modulation | GPTZero (forces "Mixed" rather than "AI") |
| Prompt-time persona tuning | ZeroGPT, Sapling |

### What the current system fails against

| Mechanism | Why It Fails |
|-----------|-------------|
| Originality.ai Turbo 3.0 | Aggressive neural classification detects underlying AI syntax |
| Pangram v3.2 EditLens | Continuous regression quantifies AI editing regardless of humanization |
| Copyleaks AI Source Match | Fixed MCP prompt templates create detectable structural repetition |
| Fast-DetectGPT | Probability curvature analysis is not defeated by syntactic variance |

### Inadvertent false-positive triggers

| Mechanism | Trigger |
|-----------|---------|
| Oregon legal boilerplate | Originality.ai interprets low-entropy domain writing as AI |
| Fixed MCP templates | Copyleaks retrieval matches repeated structural patterns |
| Forced burstiness rules | Fast-DetectGPT interprets forced variance as an adversarial signature |

---

## Forward Threat Timeline (Through 2027)

| Timeframe | Capability Evolution | Threat Level |
|-----------|---------------------|--------------|
| Q3 2026 | Universal EditLens-style regression (edit percentage vs. binary) | Critical |
| Q4 2026 | AI Source Match integrated across enterprise compliance scanners | High |
| Q1 2027 | StealthRL-immune multi-detector ensembles (RoBERTa + XLM-R) | Critical |
| Q2 2027 | Mandated cryptographic watermarking at frontier API level | Moderate |

---

## SynthID-Text (Google DeepMind Watermarking)

**Mechanism**: Tournament sampling. A pseudorandom g-function generates secret values for
each token based on a context hash from previous tokens. Tokens compete in elimination
rounds; a token advances if its generative likelihood plus its secret watermark value
defeats competitors, embedding a statistically detectable bias.

**Vulnerabilities**:
- Layer inflation attacks target the mean score of the detection strategy.
- Cross-model shifting (routing watermarked output through a non-watermarked model like
  Claude or Llama 3) destroys the token sequence and strips the watermark entirely.

**Relevance**: The pipeline's documented use of Claude insulates outputs from SynthID
tracking, provided no upstream watermarked model output (e.g., Gemini-generated text) is
ingested verbatim without local regeneration.

---

## StealthRL Threat

**Architecture**: Reinforcement learning paraphrase attack using Group Relative Policy
Optimization (GRPO) with LoRA adapters (e.g., Qwen3-4B). Optimizes paraphrasing to evade
detectors while preserving semantics.

**Performance**: Drops Binoculars and MAGE AUROC to near-random chance (97.6% attack
success rate, mean TPR 0.024 at 1% FPR).

**Industry response**: Multi-detector ensembles (RoBERTa + XLM-R + BERT) restore accuracy
to > 99% even against StealthRL. Single-model detectors are now insufficient.

---

## Prioritized Remediation Actions

Ranked by risk reduction impact:

1. **Decouple structural determinism from lexical requirements** (High risk / Medium effort):
   Separate mandatory legal/compliance vocabulary from paragraph structure. Introduce
   stochastic structural variables in MCP tool templates so repeated submissions do not
   produce identical structural fingerprints.

2. **Deprecate optimization for legacy detectors** (Low risk / Low effort): Stop benchmarking
   against ZeroGPT, Scribbr, or basic Turnitin heuristics. Benchmark exclusively against
   Pangram v3.2, Binoculars, and Fast-DetectGPT.

3. **Implement cross-model token regeneration** (Medium risk / Low effort): If text is ever
   initially drafted using a watermarked model, regenerate it completely through a
   non-watermarked model. Editing watermarked text does not strip the SynthID signal; only
   full token regeneration does.

4. **Transition toward adversarial validation** (High risk / High effort): Route drafted text
   through a local LoRA-adapted model with GRPO-style semantic preservation to shift the
   syntactic distribution away from the base model's default log-probabilities, without
   destroying semantic content.

---

## References

- Callison-Burch et al. (2024). "RAID: A Shared Benchmark for Robust Evaluation of
  Machine-Generated Text Detectors." ACL 2024. https://aclanthology.org/2024.acl-long.674/
- Dugan et al. (2025). "GenAIDetect 2025: Workshop on GenAI Content Detection." COLING 2025.
  https://aclanthology.org/events/genaidetect-2025/
- Google DeepMind (2026). "SynthID Text: Tournament Sampling."
  https://huggingface.co/blog/synthid-text
- Li et al. (2026). "Variation is the Key." arXiv:2602.13226v1.
  https://arxiv.org/html/2602.13226v1
- Pangram Research (2026). "EditLens: Quantifying the Extent of AI Editing." ICLR 2026.
  https://liner.com/review/editlens-quantifying-the-extent-of-ai-editing-in-text
- Ranganath & Ramesh (2026). "StealthRL." arXiv:2602.08934.
  https://arxiv.org/abs/2602.08934
- Verma et al. (2024). "Ghostbuster." NAACL 2024.
  https://aclanthology.org/2024.naacl-long.95/
- Zhang et al. (2026). "Tournament Sampling for SynthID-Text." arXiv:2603.03410v2.
  https://arxiv.org/html/2603.03410v2
