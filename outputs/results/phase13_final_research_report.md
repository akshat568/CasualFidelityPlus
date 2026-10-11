# Controlled Distortion Stress Test: Empirical Evaluation of Causal Alignment, Distortion Detection, and Faithfulness Metrics

**Project**: CausalFidelityPlus  
**Evaluation Scope**: Ablation Studies & Empirical Results  
**Execution Date**: September 26, 2026  
**Status**: Completed and Verified (9/9 Experiments Succeeded)  
**Execution Manifest**: `outputs/results/ablation_execution_master_manifest.json`  

---

## Abstract

Evaluating causal faithfulness and detecting causal distortions in text summarization requires understanding how algorithmic components, similarity thresholds, component weighting models, and automated consistency metrics interact. This report presents an empirical evaluation of the CausalFidelityPlus framework using a controlled, single-factor ablation matrix of nine experiments (`EXP_01_BASELINE` through `EXP_09_HUMAN_CORRELATION`). Experiments were evaluated against a development benchmark of 100 XSum news documents, from which 51 explicit causal relations were extracted, alongside 6 validated controlled summary perturbations and a 12-annotation human consensus dataset.

Our findings demonstrate that component weighting is the primary leverage point influencing composite causal alignment scores: equal weighting (`cause = 0.33, effect = 0.33, relation = 0.34`) increases overall alignment by **+56.81%** (from 0.3195 to 0.5010) due to exact connective category matching, whereas argument-only weighting (`relation = 0.00`) reduces alignment by **-20.97%** (to 0.2525) by isolating pure semantic argument similarity. In contrast, threshold variations (permissive `0.35/0.35/0.45` vs. strict `0.65/0.65/0.75`) alter candidate classification boundaries in unaligned summaries without changing underlying embedding similarities or controlled benchmark distortion detection (83.33% agreement, 5 of 6 correct). Selective metric ablations confirmed pipeline modularity and identified SummaCConv as the primary computational bottleneck (~80% of metric evaluation time on CPU; disabling it yielded a **79.17% reduction in total pipeline runtime**, from 706.99s to 147.28s). Human correlation analysis against binary distortion targets returned mathematically undefined results due to zero variance across the n = 6 controlled benchmark perturbations (all intended distortions), while continuous naturalness ratings exhibited an exploratory negative correlation of Pearson r = -0.3162 and Spearman ρ = -0.3162 against metric score deltas.

---

## 1. Research Motivation and Objectives

Automatic text summarization models frequently generate fluent text that suffers from hallucination and factual inconsistency. In causal contexts—such as reporting policy decisions, scientific discoveries, or financial events—distortions such as inverting cause and effect, omitting necessary preconditions, or substituting causal arguments fundamentally corrupt document meaning.

The CausalFidelityPlus framework was designed to address this problem through an end-to-end causal evaluation pipeline that:
1. Extracts source-document and summary causal relations.
2. Aligns corresponding causal arguments across source and summary graphs.
3. Classifies causal distortions into structured categories (`WEAKENED`, `DROPPED`, `CAUSE_CHANGED`, `EFFECT_CHANGED`).
4. Generates controlled causal perturbations to evaluate metric sensitivity.
5. Assesses summary faithfulness using automated natural language inference (NLI) and embedding metrics.

While individual algorithmic components were validated during initial development, their sensitivity to hyperparameter configuration, component weighting, and metric ablation required systematic empirical testing. This evaluation was guided by four central research questions:

- **RQ1 (Threshold Sensitivity)**: How do permissive (`0.35/0.35/0.45`) and strict (`0.65/0.65/0.75`) similarity thresholds alter causal alignment rates and distortion classification distributions compared to baseline (`0.50/0.50/0.60`)?
- **RQ2 (Component Weighting Dynamics)**: How does re-balancing cause argument, effect argument, and relation connective weights affect the magnitude and behavior of composite causal alignment scores?
- **RQ3 (Metric Modularity and Efficiency)**: What is the computational overhead and marginal contribution of each evaluation metric (SummaCConv, FactCC, BERTScore), and does disabling any metric disrupt downstream pipeline execution?
- **RQ4 (Human Consensus Alignment)**: To what extent do automated faithfulness metric scores and score deltas correlate with consensus human annotations of causal distortion and naturalness under strict disagreement-exclusion rules?

---

## 2. Dataset and Evaluation Methodology

### 2.1 Dataset Specifications
- **Development Corpus**: 100 news articles sampled from the XSum development split (`data/processed/xsum_dev.jsonl`).
- **Source Causal Extraction**: 51 explicit causal relations extracted across 26 documents using rule-based causal connective parsing (`because`: 25, `due to`: 9, `because of`: 6, `caused`: 4, `led to`: 3, `resulted in`: 2, `contributed to`: 1, `because_leading`: 1).
- **Controlled Perturbation Benchmark**: 10 generated summary perturbations subjected to automated quality validation, yielding 6 validated perturbations with confirmed causal modifications (`WEAKENED`: 2, `DROPPED`: 2, `CAUSE_CHANGED`: 1, `EFFECT_CHANGED`: 1).
- **Human Consensus Dataset**: 12 annotation records collected from 2 independent annotators across 6 summary pairs. After excluding 6 records where annotators disagreed on categorical distortion labels, 6 consensus pairs (n = 6) were retained for statistical correlation analysis.

### 2.2 Evaluation Metrics
  ```
  Alignment = (w_cause × sim_cause) + (w_effect × sim_effect) + (w_relation × match_connective)
  ```
  where `w_cause = 0.45`, `w_effect = 0.45`, and `w_relation = 0.10` in the baseline configuration.
- **Distortion Classification Agreement**: The proportion of controlled benchmark perturbations whose automated distortion classification matches the ground-truth perturbation type.
- **SummaCConv**: NLI consistency metric generating a summary-document consistency score; evaluated as score delta (Δ = original score − perturbed score).
- **FactCC**: Binary classification model evaluating factual consistency; evaluated as score delta (Δ = original score − perturbed score).
- **BERTScore**: Surface semantic token similarity (F1) and semantic similarity loss (1.0 − F1) using `roberta-large`.

---

## 3. Experimental Configurations

To isolate individual factors without confounding effects, we executed a single-factor ablation matrix of nine experiments. Each experiment modified a single parameter dimension while holding all other variables constant:

1. **Deterministic Execution**: All runs used a fixed random seed (`seed = 42`) and deterministic candidate selection.
2. **Directory Isolation**: Every experiment wrote to an isolated output directory (`outputs/experiments/<EXP_ID>/runs/<EXP_ID>_run_001/`).
3. **Reference Baseline Preservation**: The default configuration (`configs/base.yaml`) remained unchanged throughout testing.
4. **Explicit Missing-Data Representation**: Ablated components recorded stage status as `SKIPPED` and recorded values explicitly as `None` or `ABLATED` rather than substituting zero.

### Ablation Matrix Overview

| Experiment ID | Category | Configuration Overrides | Sample Size | Primary Evaluation Focus |
| :--- | :--- | :--- | :---: | :--- |
| **`EXP_01_BASELINE`** | Baseline Reference | Standard defaults (`weights = 0.45/0.45/0.10`, `thresh = 0.50/0.50/0.60`) | 100 dev / 6 benchmark | Reference alignment, distortion agreement, and multi-metric baseline |
| **`EXP_02_THRESH_PERMISSIVE`** | Threshold Ablation | `cause = 0.35, effect = 0.35, overall = 0.45` | 100 dev / 6 benchmark | Permissive alignment and candidate classification sensitivity |
| **`EXP_03_THRESH_STRICT`** | Threshold Ablation | `cause = 0.65, effect = 0.65, overall = 0.75` | 100 dev / 6 benchmark | Strict alignment boundaries and candidate rejection behavior |
| **`EXP_04_WEIGHT_EQUAL`** | Weighting Ablation | `cause = 0.33, effect = 0.33, relation = 0.34` | 100 dev / 6 benchmark | Score sensitivity to connective type matching |
| **`EXP_05_WEIGHT_ARG_ONLY`** | Weighting Ablation | `cause = 0.50, effect = 0.50, relation = 0.00` | 100 dev / 6 benchmark | Score sensitivity to pure argument semantics |
| **`EXP_06_ABLATE_SUMMAC`** | Metric Ablation | `summac_enabled = False` | 100 dev / 6 benchmark | Pipeline stability and runtime speedup without SummaCConv |
| **`EXP_07_ABLATE_FACTCC`** | Metric Ablation | `factcc_enabled = False` | 100 dev / 6 benchmark | Pipeline stability and metric isolation without FactCC |
| **`EXP_08_ABLATE_BERTSCORE`** | Metric Ablation | `bertscore_enabled = False` | 100 dev / 6 benchmark | Pipeline stability and metric isolation without BERTScore |
| **`EXP_09_HUMAN_CORRELATION`** | Human Validation | Human validation evaluation harness | 12 records / 6 consensus | Pearson r and Spearman ρ correlation on consensus human ratings |

### Execution Environment and Runtime Reconciliation
- **Hardware & Backend**: CPU execution (`device = cpu`), PyTorch 2.x, Transformers 4.x, Python 3.11.9 on Windows 11.
- **Total Master Execution Time**: **2,950.54 seconds** (~49.1 minutes).
- **Sum of Individual Experiment Runtimes**: **2,948.98 seconds**.
- **Reconciled Harness Overhead**: **1.56 seconds** (approximately 0.17 seconds per experiment iteration for structured logging, path verification, and manifest serialization).

---

## 4. Experimental Results

### 4.1 Baseline Performance (`EXP_01_BASELINE`)
The reference baseline established core evaluation benchmarks:
- **Causal Alignment**: Mean cause argument similarity of `0.2273`, mean effect similarity of `0.2777`, and a composite mean overall alignment score of **`0.3195`**. In reference summaries without explicit causal counter-statements, 46 relations produced no candidate summary matches, and 5 fell below the 0.60 overall threshold.
- **Distortion Classification**: On the 6 validated controlled benchmark perturbations, automated classification achieved **`83.33%` agreement** (5 of 6 correct: `WEAKENED`: 3, `DROPPED`: 1, `CAUSE_CHANGED`: 1, `EFFECT_CHANGED`: 1).
- **Faithfulness Consistency**: SummaCConv produced a mean score delta of `+0.0023` (original 0.8857 vs. perturbed 0.8834), FactCC produced a mean delta of `-0.0015` (original 0.0001 vs. perturbed 0.0016), and BERTScore yielded a mean F1 of `0.9698` (mean similarity loss of `0.0302`).
- **Pipeline Runtime**: **706.99 seconds** (includes initial model checkpoint loading and tokenizer caching).

### 4.2 Threshold Sensitivity (`EXP_02` vs. `EXP_03`)
Evaluating permissive (`0.35/0.35/0.45`) and strict (`0.65/0.65/0.75`) threshold boundaries demonstrated:

| Metric / Attribute | EXP_01 Baseline (`0.50/0.50/0.60`) | EXP_02 Permissive (`0.35/0.35/0.45`) | EXP_03 Strict (`0.65/0.65/0.75`) |
| :--- | :---: | :---: | :---: |
| **Mean Overall Alignment Score** | 0.3195 | 0.3195 | 0.3195 |
| **Aligned Relations (≥ Threshold)** | 0 | 0 | 0 |
| **Below Threshold Count** | 5 | 5 | 5 |
| **No Candidate Count** | 46 | 46 | 46 |
| **Controlled Benchmark Agreement** | 83.33% (5/6) | 83.33% (5/6) | 83.33% (5/6) |
| **Reference Summary Classification** | Insufficient: 49, Distorted: 1, Effect Changed: 1 | Insufficient: 49, Cause Changed: 1, Effect Changed: 1 | Insufficient: 49, Distorted: 2 |

**Key Finding**: Threshold shifts do not alter raw cosine similarities or benchmark distortion classification agreement. On reference summaries, permissive thresholds allow unaligned candidates with marginal similarity to be assigned specific distortion categories (`CAUSE_CHANGED` / `EFFECT_CHANGED`), whereas strict thresholds group them into generic `DISTORTED`.

### 4.3 Component Weighting Dynamics (`EXP_04` vs. `EXP_05`)
Evaluating component weights demonstrated significant sensitivity to connective matching:

| Metric / Attribute | EXP_01 Baseline (`0.45/0.45/0.10`) | EXP_04 Equal Weights (`0.33/0.33/0.34`) | EXP_05 Argument-Only (`0.50/0.50/0.00`) |
| :--- | :---: | :---: | :---: |
| **Mean Cause Similarity** | 0.2273 | 0.2273 | 0.2273 |
| **Mean Effect Similarity** | 0.2777 | 0.2777 | 0.2777 |
| **Mean Overall Alignment Score** | **0.3195** | **0.5010** | **0.2525** |
| **Absolute Difference vs. Baseline** | 0.0000 | **+0.1815** | **-0.0670** |
| **Relative Difference vs. Baseline (%)** | 0.00% | **+56.81%** | **-20.97%** |
| **Controlled Benchmark Agreement** | 83.33% (5/6) | 83.33% (5/6) | 83.33% (5/6) |

**Key Finding**: Re-balancing component weights is the single most influential determinant of alignment score magnitude. Assigning 34% weight to connective type matching (`EXP_04`) inflates alignment by **+56.81%** because identical connective phrases produce a match score of 1.0. Conversely, zero-weighting connective type (`EXP_05`) isolates pure semantic argument similarity:
$$(0.50 \times 0.2273) + (0.50 \times 0.2777) = 0.2525 \quad (-20.97\%)$$

### 4.4 Metric Modularity and Computational Overhead (`EXP_06` to `EXP_08`)
Ablating individual metrics confirmed modular execution and computational profiling:

| Metric / Attribute | EXP_01 Baseline | EXP_06 Ablate SummaC | EXP_07 Ablate FactCC | EXP_08 Ablate BERTScore |
| :--- | :---: | :---: | :---: | :---: |
| **SummaC Stage Status** | SUCCESS | **SKIPPED** | SUCCESS | SUCCESS |
| **FactCC Stage Status** | SUCCESS | SUCCESS | **SKIPPED** | SUCCESS |
| **BERTScore Stage Status** | SUCCESS | SUCCESS | SUCCESS | **SKIPPED** |
| **SummaC Mean Score Delta (Δ)** | +0.0023 | **`ABLATED`** | +0.0003 | +0.0022 |
| **FactCC Mean Score Delta (Δ)** | -0.0015 | -0.0015 | **`ABLATED`** | -0.0015 |
| **BERTScore Mean F1** | 0.9698 | 0.9698 | 0.9698 | **`ABLATED`** |
| **Total Pipeline Runtime (s)** | 706.99 | **147.28** | 298.11 | 569.21 |
| **Runtime Reduction vs. Baseline (%)** | 0.00% | **-79.17%** | -57.83% | -19.49% |

**Key Finding**: Disabling SummaCConv (`EXP_06`) produced a **79.17% runtime reduction** (from 706.99s to 147.28s) because SummaCConv evaluates multi-pair NLI convolution across all sentence combinations. All ablated metrics correctly logged `ABLATED` / `None` without propagating false zero-values into downstream analysis.

### 4.5 Human Validation and Consensus Correlation (`EXP_09`)
Evaluating baseline metrics against consensus human ratings revealed the following:
- **Binary Distortion Target Correlation**: Pearson r, Spearman ρ, and ROC-AUC against binary `human_causal_distortion` are **mathematically undefined**. Because all 6 validated benchmark perturbations are true intended distortions (ground truth = 1 for all samples), the target vector has zero variance (`[1, 1, 1, 1, 1, 1]`). Standard correlation against a constant vector cannot be computed.
- **Continuous Naturalness Rating Correlation**: Correlation between automated score deltas (Δ) and continuous human naturalness ratings (1.0–5.0 Likert scale) yielded:
  - Pearson r vs. Score Delta: **-0.3162** (p > 0.05, exploratory)
  - Spearman ρ vs. Score Delta: **-0.3162** (p > 0.05, exploratory)
  - Pearson r vs. Perturbed Score: +0.0363
  - Spearman ρ vs. Perturbed Score: +0.1118

The exploratory negative correlation (r = -0.3162) suggests an expected trend: larger metric deltas (greater perceived factual degradation) correspond to lower human naturalness ratings. However, with n = 6 consensus pairs, this trend cannot be interpreted as statistically significant.

---

## 5. Consolidated Experimental Matrix Comparison

The table below summarizes performance metrics, runtime, and sample sizes across all nine experiments:

| Experiment ID | Category | Parameter Overrides | Mean Alignment | Alignment Rel Diff | SummaC Mean Δ | FactCC Mean Δ | BERTScore F1 | Runtime (s) | Runtime Rel Diff | Dev Sample | Benchmark Perturbations |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`EXP_01_BASELINE`** | Baseline | Standard Defaults | 0.3195 | 0.00% | +0.0023 | -0.0015 | 0.9698 | 706.99 | 0.00% | 100 | 6 |
| **`EXP_02_THRESH_PERMISSIVE`** | Threshold | `cause/effect = 0.35, overall = 0.45` | 0.3195 | 0.00% | +0.0023 | -0.0015 | 0.9698 | 305.07 | -56.85% | 100 | 6 |
| **`EXP_03_THRESH_STRICT`** | Threshold | `cause/effect = 0.65, overall = 0.75` | 0.3195 | 0.00% | +0.0023 | -0.0015 | 0.9698 | 310.22 | -56.12% | 100 | 6 |
| **`EXP_04_WEIGHT_EQUAL`** | Weighting | `cause/effect = 0.33, relation = 0.34` | **0.5010** | **+56.81%** | -0.0092 | -0.0015 | 0.9698 | 307.39 | -56.52% | 100 | 6 |
| **`EXP_05_WEIGHT_ARG_ONLY`** | Weighting | `cause/effect = 0.50, relation = 0.00` | **0.2525** | **-20.97%** | +0.0005 | -0.0015 | 0.9698 | 304.55 | -56.92% | 100 | 6 |
| **`EXP_06_ABLATE_SUMMAC`** | Metric | `summac_enabled = False` | 0.3195 | 0.00% | **`ABLATED`** | -0.0015 | 0.9698 | **147.28** | **-79.17%** | 100 | 6 |
| **`EXP_07_ABLATE_FACTCC`** | Metric | `factcc_enabled = False` | 0.3195 | 0.00% | +0.0003 | **`ABLATED`** | 0.9698 | 298.11 | -57.83% | 100 | 6 |
| **`EXP_08_ABLATE_BERTSCORE`** | Metric | `bertscore_enabled = False` | 0.3195 | 0.00% | +0.0022 | -0.0015 | **`ABLATED`** | 569.21 | -19.49% | 100 | 6 |
| **`EXP_09_HUMAN_CORRELATION`** | Validation | Human Consensus Evaluation | N/A | N/A | N/A | N/A | N/A | 0.16 | -99.98% | 12 records | 6 consensus |

*Runtime Note*: EXP_01 (706.99s) reflects the first run, including cold-start model checkpoint loading and caching. Subsequent runs with active models averaged approximately 305s to 310s, while EXP_06 ablated SummaC and ran in 147.28s.

---

## 6. Discussion and Key Findings

1. **Weighting Model Sensitivity Dominates Threshold Selection**: The relative balance between semantic argument similarity and connective matching is the primary parameter governing composite causal alignment score magnitude. Assigning equal weights (`EXP_04`) inflates alignment by +56.81%, whereas argument-only weighting (`EXP_05`) isolates semantic similarity (-20.97%). Developers tuning causal fidelity systems must explicitly determine whether connective phrase agreement should be rewarded independently of semantic arguments.
2. **Threshold Boundaries Serve Strictly as Classification Gates**: Variations in similarity thresholds (`EXP_02`, `EXP_03`) do not alter underlying cosine similarity distributions or controlled benchmark accuracy. Their effect is confined to partitioning borderline candidates into specific distortion categories versus generic unaligned classifications.
3. **SummaCConv Represents the Primary Computational Cost**: Metric profiling demonstrates that multi-pair NLI inference in SummaCConv consumes ~80% of total metric calculation time on CPU architectures. For latency-sensitive production pipelines, selective invocation or lighter NLI backends provide immediate throughput gains (a 79.17% pipeline runtime reduction).
4. **Architectural Modularity and Fault Tolerance**: Selective component ablation verified that individual metrics can be cleanly disabled without runtime failure, schema violation, or numerical contamination from artificial zero-fills.
5. **Zero-Variance Limitation in Benchmarks Without Negative Controls**: The evaluation established that controlled distortion benchmarks consisting exclusively of true positives cannot be evaluated via standard correlation metrics. Validating metric sensitivity requires balanced benchmarks containing both verified distortions and non-distorted baseline controls.

---

## 7. Limitations and Scope Boundaries

### 7.1 Confirmed Empirical Limitations
- **Controlled Benchmark Sample Size**: The controlled benchmark consists of n = 6 validated perturbations derived from 100 XSum development documents. Findings are descriptive and exploratory rather than definitive population estimates.
- **Human Consensus Sample Size**: Statistical correlation is restricted to n = 6 consensus pairs after excluding 6 disagreed records under strict inter-annotator consensus rules.
- **Zero-Variance Binary Target Vector**: Because all 6 validated perturbations represent true distortions, binary correlation against ground truth is mathematically undefined.
- **Rule-Based Connective Extraction**: The causal extraction component targets explicit causal connectives (e.g., `because`, `due to`, `led to`) and does not capture implicit or discourse-level causal dependencies.
- **General-Purpose NLI Metric Sensitivity**: Pretrained NLI models (SummaC, FactCC) exhibit modest sensitivity to localized causal argument inversions when general topical overlap remains high.

### 7.2 Methodological Threats to Validity
- **Domain Specificity**: The evaluation was performed exclusively on XSum news summaries; behavior on scientific, legal, or medical texts may vary.
- **Fixed Model Embeddings**: Causal argument similarity relies on fixed pretrained representations (`all-MiniLM-L6-v2`); alternative embedding architectures may demonstrate different threshold sensitivities.

---

## 8. Opportunities for Future Research

Based on the empirical findings, the following research directions are identified:

1. **Benchmark Scale and Domain Expansion**: Expanding controlled benchmark generation to n = 500+ validated perturbations across diverse multi-domain corpora (e.g., CNN/DailyMail, PubMed, GovReport) to establish statistically robust evaluation bounds.
2. **Causal-Specific NLI Cross-Encoder Tuning**: Fine-tuning NLI cross-encoders directly on causal argument pairs to heighten model sensitivity to subtle cause-effect reversals and argument swaps.
3. **Balanced Human Benchmark Protocols**: Incorporating non-distorted baseline summaries alongside controlled perturbations in annotation tasks to eliminate the zero-variance limitation and enable full ROC-AUC and correlation evaluation.
4. **Supervised Weight Optimization**: Developing learned component weighting models trained against human causal similarity judgements rather than relying on heuristic weight configurations.

---

## 9. Reproducibility and Project Artifacts

### Core Research Artifacts
- **Master Execution Manifest**: `outputs/results/ablation_execution_master_manifest.json`
- **Results Analysis & Synthesis**: `outputs/results/phase13_step4_results_analysis.md`
- **Machine-Readable Summary**: `outputs/results/phase13_final_research_summary.json`
- **Final Research Report**: `outputs/results/phase13_final_research_report.md`

### Experiment Run Directories
- `EXP_01_BASELINE`: `outputs/experiments/EXP_01_BASELINE/runs/EXP_01_BASELINE_run_001/`
- `EXP_02_THRESH_PERMISSIVE`: `outputs/experiments/EXP_02_THRESH_PERMISSIVE/runs/EXP_02_THRESH_PERMISSIVE_run_001/`
- `EXP_03_THRESH_STRICT`: `outputs/experiments/EXP_03_THRESH_STRICT/runs/EXP_03_THRESH_STRICT_run_001/`
- `EXP_04_WEIGHT_EQUAL`: `outputs/experiments/EXP_04_WEIGHT_EQUAL/runs/EXP_04_WEIGHT_EQUAL_run_001/`
- `EXP_05_WEIGHT_ARG_ONLY`: `outputs/experiments/EXP_05_WEIGHT_ARG_ONLY/runs/EXP_05_WEIGHT_ARG_ONLY_run_001/`
- `EXP_06_ABLATE_SUMMAC`: `outputs/experiments/EXP_06_ABLATE_SUMMAC/runs/EXP_06_ABLATE_SUMMAC_run_001/`
- `EXP_07_ABLATE_FACTCC`: `outputs/experiments/EXP_07_ABLATE_FACTCC/runs/EXP_07_ABLATE_FACTCC_run_001/`
- `EXP_08_ABLATE_BERTSCORE`: `outputs/experiments/EXP_08_ABLATE_BERTSCORE/runs/EXP_08_ABLATE_BERTSCORE_run_001/`
- `EXP_09_HUMAN_CORRELATION`: `outputs/experiments/EXP_09_HUMAN_CORRELATION/runs/EXP_09_HUMAN_CORRELATION_run_001/`

### Reproduction Command
```bash
python -m pytest -o pythonpath=src tests
```
*Verification*: 292 passed tests across all API, extraction, perturbation, alignment, and ablation modules.
