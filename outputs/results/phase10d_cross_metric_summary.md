# Phase 10D — Research Analysis and Cross-Metric Comparison Report

## 1. Executive Summary & Benchmark Context

- **Total Valid Perturbations Evaluated:** 6
- **Total Invalid Perturbations Excluded:** 4
- **Unique Source Documents:** 2 (`xsum_000038, xsum_000074`)
- **Sample Size Warning:** $n=6$ small development benchmark size across 2 source documents. Results are strictly descriptive and preliminary.

## 2. Metric Score Semantics & Response Definitions

1. **SummaCConv (NLI Consistency):** $\Delta_{\text{SummaC}} = \text{orig} - \text{pert}$. Positive delta indicates consistency drop.
2. **FactCC (Factual Classification):** $\Delta_{\text{FactCC}} = \text{orig} - \text{pert}$. Positive delta indicates predicted correctness drop.
3. **BERTScore (Semantic Control):** $F_1 \in [0, 1]$ and $\text{Similarity Loss} = 1.0 - F_1$. Measures surface token embedding divergence.

## 3. Verified Per-Perturbation Results

| Perturbation ID | Doc ID | Intended Type | Detected Label | SummaC $\Delta$ | FactCC $\Delta$ | BERTScore $F_1$ | BERTScore Loss |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `xsum_000038_pert_000002` | `xsum_000038` | `WEAKENED` | `WEAKENED` | `+0.0000` | `-0.0030` | `0.9875` | `0.0125` |
| `xsum_000038_pert_000003` | `xsum_000038` | `DROPPED` | `WEAKENED` | `+0.0000` | `-0.0059` | `0.9858` | `0.0142` |
| `xsum_000038_pert_000005` | `xsum_000038` | `EFFECT_CHANGED` | `EFFECT_CHANGED` | `+0.0176` | `-0.0004` | `0.9205` | `0.0795` |
| `xsum_000074_pert_000007` | `xsum_000074` | `WEAKENED` | `WEAKENED` | `+0.0000` | `-0.0000` | `0.9869` | `0.0131` |
| `xsum_000074_pert_000008` | `xsum_000074` | `DROPPED` | `DROPPED` | `+0.0000` | `-0.0000` | `0.9926` | `0.0074` |
| `xsum_000074_pert_000009` | `xsum_000074` | `CAUSE_CHANGED` | `CAUSE_CHANGED` | `+0.0000` | `-0.0000` | `0.9456` | `0.0544` |

## 4. Aggregate Metric Performance Summary

- **SummaCConv:** Mean $\Delta = +0.0029$, Median $\Delta = +0.0000$ (Positive: 1, Zero: 5, Negative: 0)
- **FactCC:** Mean $\Delta = -0.0015$, Median $\Delta = -0.0002$ (Positive: 0, Zero: 3, Negative: 3)
- **BERTScore:** Mean $F_1 = 0.9698$, Mean Similarity Loss = 0.0302

## 5. Perturbation-Type Breakdown

### `WEAKENED` ($n=2$)
- **SummaCConv Mean $\Delta$:** `+0.0000`
- **FactCC Mean $\Delta$:** `-0.0015`
- **BERTScore Mean $F_1$:** `0.9872`
- **BERTScore Mean Similarity Loss:** `0.0128`
- **Detected Label Distribution:** `{'WEAKENED': 2}`

### `DROPPED` ($n=2$)
- **SummaCConv Mean $\Delta$:** `+0.0000`
- **FactCC Mean $\Delta$:** `-0.0029`
- **BERTScore Mean $F_1$:** `0.9892`
- **BERTScore Mean Similarity Loss:** `0.0108`
- **Detected Label Distribution:** `{'WEAKENED': 1, 'DROPPED': 1}`

### `EFFECT_CHANGED` ($n=1$) *(Single Observation)*
- **SummaCConv Mean $\Delta$:** `+0.0176`
- **FactCC Mean $\Delta$:** `-0.0004`
- **BERTScore Mean $F_1$:** `0.9205`
- **BERTScore Mean Similarity Loss:** `0.0795`
- **Detected Label Distribution:** `{'EFFECT_CHANGED': 1}`

### `CAUSE_CHANGED` ($n=1$) *(Single Observation)*
- **SummaCConv Mean $\Delta$:** `+0.0000`
- **FactCC Mean $\Delta$:** `+0.0000`
- **BERTScore Mean $F_1$:** `0.9456`
- **BERTScore Mean Similarity Loss:** `0.0544`
- **Detected Label Distribution:** `{'CAUSE_CHANGED': 1}`

### `REVERSED` ($n=0$)
- *Coverage:* No valid perturbations available in current dev benchmark for this category.

## 6. Key Descriptive Research Observations

1. **Metric Blindness to Subtle Causal Phrase Swaps:** Both SummaCConv and FactCC exhibited zero or negative response to `WEAKENED` and `DROPPED` causal phrase modifications.
2. **BERTScore Reflects Surface Divergence, Not Faithfulness:** BERTScore $F_1$ remains high ($\\ge 0.985$) for `WEAKENED` and `DROPPED` phrase edits, but drops noticeably ($F_1 = 0.9205$) for clause substitution (`EFFECT_CHANGED`).
3. **Absence of REVERSED Examples:** No validated `REVERSED` perturbations exist in the current benchmark, representing an essential target for expanded benchmark generation.

## 7. Limitations & Scope Constraints

- Results are strictly preliminary and descriptive ($n=6$).
- No statistical significance or general metric superiority claims are made.
- BERTScore functions solely as a semantic similarity control.
