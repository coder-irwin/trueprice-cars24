"""
variant_resolver.py — evidence-based variant disambiguation (Pillar 1).

The CEO's #1 driver of the estimate-to-final gap: "4 out of 10 inspected cars show a
different variant than the seller entered online ... can shift the price by 15-20%."
You cannot fix that by asking "which variant?" harder — sellers genuinely don't know
their trim name. So we resolve it from *evidence the seller can actually see*: visible
features (sunroof, alloys, touchscreen, airbags, ...).

Algorithm (a small, honest Bayesian disambiguator):
  - Prior: all variants of the model equally likely.
  - Each feature answer updates a soft likelihood (soft, because sellers misremember).
  - We always ask the UNANSWERED feature with the highest expected information gain, so
    we reach certainty in the fewest questions.
  - We stop when the top variant's posterior clears a confidence threshold, or we run
    out of discriminating questions — and we report the leftover uncertainty honestly.

Pure functions, no framework deps → trivially testable (see tests/).
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional

from catalog import get_model, FEATURE_QUESTIONS, reference_price

# Soft-evidence likelihoods: P(answer | variant) when the answer matches the variant's
# true feature vs when it doesn't. Not 1.0/0.0 because sellers occasionally misremember.
_MATCH = 0.96
_MISMATCH = 0.04

RESOLVED_THRESHOLD = 0.85   # posterior at which we consider the variant pinned


def _entropy(probs: List[float]) -> float:
    return -sum(p * math.log(p) for p in probs if p > 0)


def _posterior(variants, answers: Dict[str, object]) -> List[float]:
    """Posterior probability over variants given the answers so far."""
    scores = []
    for v in variants:
        logp = 0.0
        for feat, ans in answers.items():
            if feat not in v.features:
                continue
            logp += math.log(_MATCH if v.features[feat] == ans else _MISMATCH)
        scores.append(logp)
    # softmax-normalise in a numerically stable way
    m = max(scores)
    exps = [math.exp(s - m) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def _expected_entropy_after(variants, post: List[float], feat: str) -> float:
    """Expected posterior entropy if we ask `feat` next (lower = more informative)."""
    # Distribution over possible answers under current posterior.
    answer_mass: Dict[object, float] = {}
    for v, p in zip(variants, post):
        val = v.features.get(feat)
        answer_mass[val] = answer_mass.get(val, 0.0) + p

    expected = 0.0
    for val, mass in answer_mass.items():
        if mass <= 0:
            continue
        # Posterior restricted to candidates consistent with this answer.
        updated = []
        for v, p in zip(variants, post):
            like = _MATCH if v.features.get(feat) == val else _MISMATCH
            updated.append(p * like)
        z = sum(updated)
        if z <= 0:
            continue
        updated = [u / z for u in updated]
        expected += mass * _entropy(updated)
    return expected


def resolve(make: str, model: str, answers: Optional[Dict[str, object]] = None,
            fuel: str = "petrol", transmission: str = "manual") -> dict:
    """Resolve the variant given the answers gathered so far.

    Returns a dict with: candidates (ranked, with posterior + price), confidence,
    resolved (bool), next_question (or None), and a price_spread that quantifies how
    much money the remaining variant uncertainty is worth.
    """
    answers = dict(answers or {})
    m = get_model(make, model)
    if not m:
        raise ValueError(f"Unknown model: {make} {model}")

    variants = m.variants
    post = _posterior(variants, answers)

    ranked = sorted(
        [
            {
                "variant": v.name,
                "posterior": round(p, 4),
                "price_new": reference_price(make, model, v.name, fuel, transmission),
                "trim_rank": v.trim_rank,
            }
            for v, p in zip(variants, post)
        ],
        key=lambda d: d["posterior"], reverse=True,
    )

    top = ranked[0]
    confidence = top["posterior"]
    resolved = confidence >= RESOLVED_THRESHOLD

    # How much money is the *remaining* variant uncertainty worth? Posterior-weighted
    # spread of reference prices across still-plausible variants. This feeds the honest
    # range widening in pricing.py.
    plausible = [r for r in ranked if r["posterior"] >= 0.05]
    prices = [r["price_new"] for r in plausible]
    price_spread = (max(prices) - min(prices)) if len(prices) > 1 else 0

    # Choose the next question: the unanswered feature with the biggest info gain, and
    # only if it actually discriminates among still-plausible variants.
    next_question = None
    if not resolved:
        unanswered = [f for f in FEATURE_QUESTIONS if f not in answers]
        best_feat, best_score = None, None
        cur_entropy = _entropy(post)
        for feat in unanswered:
            # Skip features that don't split the plausible set at all.
            vals = {v.features.get(feat) for v, p in zip(variants, post) if p >= 0.05}
            if len(vals) < 2:
                continue
            exp_ent = _expected_entropy_after(variants, post, feat)
            gain = cur_entropy - exp_ent
            if best_score is None or gain > best_score:
                best_score, best_feat = gain, feat
        if best_feat is not None and best_score and best_score > 1e-6:
            q = FEATURE_QUESTIONS[best_feat]
            next_question = {
                "feature": best_feat,
                "question": q["question"],
                "options": [{"value": val, "label": lbl}
                            for val, lbl in q["options"].items()],
            }

    return {
        "make": make,
        "model": model,
        "candidates": ranked,
        "top_variant": top["variant"],
        "confidence": round(confidence, 4),
        "resolved": resolved,
        "next_question": next_question,
        "price_spread": price_spread,
        "answers": answers,
    }
