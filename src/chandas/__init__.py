# -*- coding: utf-8 -*-
"""
Chandas — Sanskrit prosody: syllable extraction and meter identification.

A Python port of the Prasadam / Bhakta Bandhu TypeScript chandas engine. The
public surface is deliberately small:

    analyze_verse(text)      -> per-syllable scansion with source spans
    identify_meter(analysis) -> ranked, verified meter candidates
    scan_verse(text)         -> both, in one call

Every syllable carries the rule that decided its weight and that rule's
citation; every meter verdict carries its source and, where the mūla and
bhāṣya are both keyed in, its authority pair. Both stages run an independent
maker–checker pass and downgrade the verdict rather than present an
unverified one.
"""

from .catalog import (
    CLASSICAL_VARNA_METERS,
    ClassicalVarnaMeterSpec,
    expand_gana_pattern,
    meter_by_id,
    validate_chandas_catalog,
)
from .core import (
    AKSARA_RULES,
    METER_CATALOG,
    Aksara,
    AksaraContext,
    AksaraJudgement,
    AksaraParts,
    ChandasError,
    DevaCluster,
    MeterResult,
    MeterSpec,
    annotate_deva_word,
    annotate_iast_line,
    classify_aksara,
    classify_aksara_deva,
    classify_aksara_iast,
    deva_chant_lines,
    deva_yati_in_word,
    deva_yati_word_boundary,
    identify_meter as identify_meter_from_lines,
    meter_template,
    split_deva_word_head,
    split_iast_word_head,
    syllabify_iast_line,
    yati_word_boundary,
)
from .identification import identify_sanskrit_meter
from .types import (
    SanskritMeterCandidate,
    SanskritMeterIdentification,
    to_dict,
)
from .verse_analysis import (
    AnalyzedSanskritPada,
    AnalyzedSanskritSyllable,
    SanskritVerseAnalysis,
    analyze_sanskrit_verse,
)

__all__ = [
    "AKSARA_RULES",
    "Aksara",
    "AksaraContext",
    "AksaraJudgement",
    "AksaraParts",
    "AnalyzedSanskritPada",
    "AnalyzedSanskritSyllable",
    "CLASSICAL_VARNA_METERS",
    "ChandasError",
    "ClassicalVarnaMeterSpec",
    "DevaCluster",
    "METER_CATALOG",
    "MeterResult",
    "MeterSpec",
    "SanskritMeterCandidate",
    "SanskritMeterIdentification",
    "SanskritVerseAnalysis",
    "analyze_sanskrit_verse",
    "analyze_verse",
    "chandas_report",
    "annotate_deva_word",
    "annotate_iast_line",
    "classify_aksara",
    "classify_aksara_deva",
    "classify_aksara_iast",
    "deva_chant_lines",
    "deva_yati_in_word",
    "deva_yati_word_boundary",
    "expand_gana_pattern",
    "identify_meter_from_lines",
    "identify_sanskrit_meter",
    "meter_by_id",
    "meter_label",
    "meter_summary",
    "meter_template",
    "scan_verse",
    "split_deva_word_head",
    "split_iast_word_head",
    "syllabify_iast_line",
    "to_dict",
    "validate_chandas_catalog",
    "yati_word_boundary",
]

# Friendlier aliases for the two entry points.
analyze_verse = analyze_sanskrit_verse


def scan_verse(text, script="auto", boundary_mode="auto", tradition="auto",
               include_near=True):
    """
    Convenience: analyse a verse and identify its meter in one call.

    Returns ``(analysis, identification)``. The identification is always
    present; when the analysis failed it carries status "invalid-analysis"
    with the reason in its diagnostics.
    """
    analysis = analyze_sanskrit_verse(text, script=script, boundary_mode=boundary_mode)
    identification = identify_sanskrit_meter(
        analysis, tradition=tradition, include_near=include_near
    )
    return analysis, identification


def meter_summary(text, script="auto", boundary_mode="auto", tradition="auto"):
    """
    A compact, JSON-ready summary for callers that want the verdict plus a
    little supporting evidence but not the full apparatus.

    Never raises: unscannable input comes back with ``ok: False``, the
    diagnostics that explain why, and ``label: "unidentified metre"``. That
    keeps a bad line from taking down a whole verse pipeline.
    """
    try:
        analysis, identification = scan_verse(
            text, script=script, boundary_mode=boundary_mode, tradition=tradition
        )
    except Exception as error:  # the engine raises on genuinely unknown input
        return {
            "ok": False,
            "label": "unidentified metre",
            "status": "invalid-analysis",
            "identified": False,
            "diagnostics": [str(error)],
            "padas": [],
            "totals": {},
        }

    primary = identification.primary
    count_class = (
        primary.classification.count_class
        if primary and primary.classification
        else None
    )
    return {
        "ok": analysis.ok,
        "label": meter_label(identification),
        "status": identification.status,
        "identified": identification.identified,
        "script": analysis.script,
        "boundary_mode": analysis.boundary_mode,
        "name": primary.name if primary else None,
        "kind": primary.kind if primary else None,
        "tradition": primary.tradition if primary else None,
        "match_type": primary.match_type if primary else None,
        "count_class": (
            {
                "name": count_class.name,
                "syllables_per_pada": count_class.syllables_per_pada,
            }
            if count_class
            else None
        ),
        "gana_formula": (
            primary.classification.gana_formula
            if primary and primary.classification
            else None
        ),
        "template": primary.template if primary else None,
        "yati": list(primary.yati) if primary and primary.yati else None,
        "subtypes": list(primary.subtypes) if primary and primary.subtypes else None,
        "source": (
            {"work": primary.source.work, "locator": primary.source.locator}
            if primary
            else None
        ),
        "authority_coverage": (
            primary.authority.coverage if primary and primary.authority else None
        ),
        "padas": [
            {
                "index": pada.index,
                "pattern": pada.pattern,
                "syllables": len(pada.syllables),
                "matras": pada.matras,
                "iast": pada.normalized_iast,
            }
            for pada in analysis.padas
        ],
        "totals": {
            "padas": analysis.totals.padas,
            "syllables": analysis.totals.syllables,
            "laghu": analysis.totals.laghu,
            "guru": analysis.totals.guru,
            "matras": analysis.totals.matras,
        },
        "verification": {
            "analysis": analysis.verification.status,
            "meter": identification.verification.status,
        },
        "diagnostics": [item.message for item in analysis.diagnostics]
        + list(identification.diagnostics),
    }


def chandas_report(text, script="auto", boundary_mode="auto", tradition="auto",
                   include_near=True):
    """
    The full apparatus as plain JSON-ready data: every akṣara with its weight,
    mātrā count, deciding rule and citation, plus the ranked meter candidates
    and both verification records. This is what the HTTP API serves.

    Never raises — a failure comes back as ``ok: False`` with diagnostics.
    """
    try:
        analysis, identification = scan_verse(
            text,
            script=script,
            boundary_mode=boundary_mode,
            tradition=tradition,
            include_near=include_near,
        )
    except Exception as error:
        return {
            "ok": False,
            "source_text": text,
            "padas": [],
            "totals": {},
            "diagnostics": [
                {"severity": "error", "code": "ENGINE_ERROR", "message": str(error)}
            ],
            "meter": None,
            "rules": _rule_reference(),
        }

    return {
        "ok": analysis.ok,
        "source_text": analysis.source_text,
        "script": analysis.script,
        "boundary_mode": analysis.boundary_mode,
        "normalized_text": analysis.normalized_text,
        "padas": [
            {
                "index": pada.index,
                "source": pada.source,
                "normalized_iast": pada.normalized_iast,
                "pattern": pada.pattern,
                "matras": pada.matras,
                "boundary": pada.boundary,
                "syllables": [
                    {
                        "index": s.index,
                        "position": s.position,
                        "text": s.text,
                        "iast": s.iast,
                        "devanagari": s.devanagari,
                        "source": s.source,
                        "weight": s.weight,
                        "matras": s.matras,
                        "rule": s.rule,
                        "reason": s.reason,
                        "anceps": s.anceps,
                        "pluta": s.pluta,
                        "parts": {
                            "onset": s.parts.onset,
                            "vowel": s.parts.vowel,
                            "mark": s.parts.mark,
                            "coda": s.parts.coda,
                        },
                        "span": {"start": s.span.start, "end": s.span.end},
                        "verified": s.verified,
                    }
                    for s in pada.syllables
                ],
            }
            for pada in analysis.padas
        ],
        "totals": {
            "padas": analysis.totals.padas,
            "syllables": analysis.totals.syllables,
            "laghu": analysis.totals.laghu,
            "guru": analysis.totals.guru,
            "matras": analysis.totals.matras,
        },
        "diagnostics": [
            {"severity": d.severity, "code": d.code, "message": d.message}
            for d in analysis.diagnostics
        ],
        "verification": {
            "analysis": {
                "status": analysis.verification.status,
                "checks": analysis.verification.checks,
                "checked_syllables": analysis.verification.checked_syllables,
                "method": analysis.verification.method,
                "issues": [
                    {"code": i.code, "message": i.message}
                    for i in analysis.verification.issues
                ],
            },
            "meter": {
                "status": identification.verification.status,
                "checks": identification.verification.checks,
                "method": identification.verification.method,
                "issues": [
                    {"code": i.code, "message": i.message}
                    for i in identification.verification.issues
                ],
            },
        },
        "meter": {
            "label": meter_label(identification),
            "status": identification.status,
            "identified": identification.identified,
            "requested_tradition": identification.requested_tradition,
            "catalog_size": identification.catalog_size,
            "observed_unit_patterns": identification.observed_unit_patterns,
            "diagnostics": identification.diagnostics,
            "primary": to_dict(identification.primary)
            if identification.primary
            else None,
            "candidates": [to_dict(c) for c in identification.candidates],
        },
        "rules": _rule_reference(),
    }


def _rule_reference():
    """The deciding-rule legend, so a UI can show why each syllable scanned as it did."""
    return {
        key: {"plain": rule.plain, "sutra": rule.sutra}
        for key, rule in AKSARA_RULES.items()
    }


def meter_label(identification) -> str:
    """
    A single human-readable line for the verdict — what a caller that only has
    room for one string should print. Never overstates: a provisional or
    ambiguous verdict says so.
    """
    primary = identification.primary
    if not primary:
        return "unidentified metre"
    name = primary.name
    count = primary.classification.count_class if primary.classification else None
    # Don't repeat the count class when the meter's own name already carries it
    # ("anuṣṭubh (śloka)" must not become "anuṣṭubh (śloka) (anuṣṭubh — 8 …)").
    if count and count.name.lower() in name.lower():
        klass = f" — {count.syllables_per_pada} akṣara"
    elif count:
        klass = f" ({count.name} — {count.syllables_per_pada} akṣara)"
    else:
        klass = ""
    status = identification.status
    if status == "identified":
        return f"{name}{klass}"
    if status == "provisional":
        return f"{name}{klass} — provisional"
    if status == "ambiguous":
        return f"{name}{klass} — ambiguous"
    if status == "insufficient-evidence":
        return f"{name}{klass} — fragment only"
    return "unidentified metre"
