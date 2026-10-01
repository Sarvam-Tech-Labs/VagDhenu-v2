# -*- coding: utf-8 -*-
"""
Classical varṇa-meter facts used by the meter matcher.

Ported from Prasadam's lib/chandas-meter-catalog.ts.

This module intentionally contains data and validation only. The names and
patterns are independently represented from the source transcriptions; no
source implementation is copied. A pattern records the canonical written G/L
form. Terminal licences are stored per witness-facing definition rather than
flattened into a universal final "X".
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

ClassicalVarnaMeterKind = str  # "sama-vrtta" | "ardhasama-vrtta" | "visama-vrtta" | "dandaka"
ClassicalTerminalPolicy = str  # "fixed" | "short-to-guru" | "bidirectional"


@dataclass(frozen=True)
class ChandasSourceRef:
    work: str
    locator: str
    note: Optional[str] = None


@dataclass(frozen=True)
class ClassicalVarnaMeterSpec:
    id: str
    name: str
    aliases: Tuple[str, ...]
    kind: ClassicalVarnaMeterKind
    #: Source gaṇa expressions retained for audit and display.
    gana_patterns: Tuple[str, ...]
    #: One form for sama/daṇḍaka, odd/even forms for ardhasama, four for viṣama.
    pada_patterns: Tuple[str, ...]
    terminal_policy: ClassicalTerminalPolicy
    #: Backward-compatible convenience for either non-fixed terminal policy.
    final_anceps: bool
    source: ChandasSourceRef
    #: Caesura positions per pāda form, only when the cited source fixes them.
    yati: Optional[Tuple[Tuple[int, ...], ...]] = None


@dataclass(frozen=True)
class ChandasCatalogValidation:
    valid: bool
    errors: Tuple[str, ...]


GANA_WEIGHTS: Dict[str, str] = {
    "y": "LGG",
    "m": "GGG",
    "t": "GGL",
    "r": "GLG",
    "j": "LGL",
    "b": "GLL",
    "n": "LLL",
    "s": "LLG",
    "G": "G",
    "L": "L",
}


def expand_gana_pattern(pattern: str) -> str:
    """Expands traditional ya-ma-ta-ra-ja-bha-na-sa notation into uppercase G/L."""
    expanded = ""
    for symbol in unicodedata.normalize("NFC", pattern):
        if symbol.isspace() or symbol in ("-", "_", "·"):
            continue
        weights = GANA_WEIGHTS.get(symbol)
        if not weights:
            raise ValueError(f"Unknown gaṇa-pattern symbol: {symbol!r}")
        expanded += weights
    if expanded == "":
        raise ValueError("A gaṇa pattern cannot be empty.")
    return expanded


def _define_meter(
    id: str,
    name: str,
    kind: ClassicalVarnaMeterKind,
    pattern_codes: Sequence[str],
    source: ChandasSourceRef,
    aliases: Sequence[str] = (),
    terminal_policy: Optional[ClassicalTerminalPolicy] = None,
    final_anceps: Optional[bool] = None,
    yati: Optional[Sequence[Sequence[int]]] = None,
) -> ClassicalVarnaMeterSpec:
    policy = terminal_policy or ("fixed" if final_anceps is False else "bidirectional")
    return ClassicalVarnaMeterSpec(
        id=id,
        name=name,
        aliases=tuple(aliases),
        kind=kind,
        gana_patterns=tuple(pattern_codes),
        pada_patterns=tuple(expand_gana_pattern(code) for code in pattern_codes),
        terminal_policy=policy,
        final_anceps=policy != "fixed",
        yati=tuple(tuple(positions) for positions in yati) if yati else None,
        source=source,
    )


def _sama_source(syllables: int) -> ChandasSourceRef:
    return ChandasSourceRef(
        work="V. S. Apte, Appendix A, Sanskrit Prosody",
        locator=f"sama-vṛtta table, {syllables}-akṣara class",
        note="The table's final G/L alternation is recorded in its canonical heavy form.",
    )


def _sama(
    id: str,
    name: str,
    syllables: int,
    pattern_code: str,
    aliases: Sequence[str] = (),
    yati: Optional[Sequence[int]] = None,
    terminal_policy: Optional[ClassicalTerminalPolicy] = None,
) -> ClassicalVarnaMeterSpec:
    return _define_meter(
        id=id,
        name=name,
        kind="sama-vrtta",
        pattern_codes=[pattern_code],
        aliases=aliases,
        terminal_policy=terminal_policy,
        yati=[yati] if yati else None,
        source=_sama_source(syllables),
    )


def _ck_source(ray: str, verse: str) -> ChandasSourceRef:
    return ChandasSourceRef(work=f"Chandaḥ-kaustubha, {ray}", locator=verse)


def _ardhasama(
    id: str,
    name: str,
    odd_pattern: str,
    even_pattern: str,
    verse: int,
    aliases: Sequence[str] = (),
) -> ClassicalVarnaMeterSpec:
    return _define_meter(
        id=id,
        name=name,
        kind="ardhasama-vrtta",
        pattern_codes=[odd_pattern, even_pattern],
        aliases=aliases,
        source=_ck_source("Third Ray (ardhasama-vṛtta)", f"v. {verse}"),
    )


def _visama(
    id: str,
    name: str,
    patterns: Sequence[str],
    verse: str,
    aliases: Sequence[str] = (),
) -> ClassicalVarnaMeterSpec:
    return _define_meter(
        id=id,
        name=name,
        kind="visama-vrtta",
        pattern_codes=list(patterns),
        aliases=aliases,
        source=_ck_source("Fourth Ray (viṣama-vṛtta)", verse),
    )


def _dandaka(id: str, name: str, pattern: str, verse: str) -> ClassicalVarnaMeterSpec:
    return _define_meter(
        id=id,
        name=name,
        kind="dandaka",
        pattern_codes=[pattern],
        source=_ck_source("Second Ray (daṇḍaka)", verse),
    )


def _repha_dandaka(id: str, name: str, repha_count: int, verse: str) -> ClassicalVarnaMeterSpec:
    return _dandaka(id, name, "nn" + "r" * repha_count, verse)


SAMA_METERS: Tuple[ClassicalVarnaMeterSpec, ...] = (
    _sama("kanya", "kanyā", 4, "mG"),
    _sama("pankti", "paṅkti", 5, "bGG"),

    _sama("tanumadhyama", "tanumadhyamā", 6, "ty"),
    _sama("vidyullekha", "vidyullekhā", 6, "mm", ["vāṇī"]),
    _sama("shashivadana", "śaśivadanā", 6, "ny"),
    _sama("somaraji", "somarājī", 6, "yy"),

    _sama("kumaralalita", "kumāralalitā", 7, "jsG"),
    _sama("madalekha", "madalekhā", 7, "msG"),
    _sama("madhumati", "madhumatī", 7, "nnG"),

    _sama("gajagati", "gajagati", 8, "nbLG"),
    _sama("pramanika", "pramāṇikā", 8, "jrLG"),
    _sama("manavaka", "māṇavaka", 8, "btLG"),
    _sama("vidyumala", "vidyumālā", 8, "mmGG"),

    _sama("bhujagashishubhrta", "bhujagaśiṣubhṛtā", 9, "nnm"),
    _sama("bhujangasangata", "bhujaṅgasaṅgatā", 9, "sjr"),
    _sama("manimadhya", "maṇimadhya", 9, "bms"),

    _sama("tvaritagati", "tvaritagati", 10, "njnG"),
    _sama("matta", "mattā", 10, "mbsG"),
    _sama("rukmavati", "rukmavatī", 10, "bmsG"),

    _sama("indravajra", "indravajrā", 11, "ttjGG", [], None, "short-to-guru"),
    _sama("upendravajra", "upendravajrā", 11, "jtjGG", [], None, "short-to-guru"),
    _sama("dodhaka", "dodhaka", 11, "bbbGG"),
    _sama("bhramaravilasita", "bhramaravilasita", 11, "mbnLG"),
    _sama("rathoddhata", "rathoddhatā", 11, "rnrLG"),
    _sama("vatormi", "vātormī", 11, "mbtGG"),
    _sama("shalini", "śālinī", 11, "mttGG"),
    _sama("svagata", "svāgatā", 11, "rnbGG"),

    _sama("indravamsa", "indravaṃśā", 12, "ttjr", ["indravaṁśā"]),
    _sama("candravatma", "candravatma", 12, "rnbs"),
    _sama("jaladharamala", "jaladharamālā", 12, "mbsm"),
    _sama("jaloddhatagati", "jaloddhatagati", 12, "jsjs"),
    _sama("tamarasa", "tāmarasa", 12, "njjy"),
    _sama("totaka", "toṭaka", 12, "ssss"),
    _sama("drutavilambita", "drutavilambita", 12, "nbbr"),
    _sama("pramuditavadana", "pramuditavadanā", 12, "nnrr", ["prabhā", "mandākinī"]),
    _sama("pramitakshara", "pramitākṣarā", 12, "sjss"),
    _sama("bhujangaprayata", "bhujaṅgaprayāta", 12, "yyyy"),
    _sama("manimala", "maṇimālā", 12, "tyty"),
    _sama("malati", "mālatī", 12, "njjr"),
    _sama("vamsastha", "vaṃśastha", 12, "jtjr", ["vaṁśastha"]),
    _sama("vaishvadevi", "vaiśvadevī", 12, "mmyy"),
    _sama("sragvini", "sragviṇī", 12, "rrrr"),
    _sama("patuvrtta", "paṭuvṛtta", 12, "nnmy"),

    _sama("kalahamsa", "kalahaṃsa", 13, "sjssG", ["siṃhanāda", "kuṭajā"]),
    _sama("kshama", "kṣamā", 13, "nnttG", ["candrikā", "utpalinī"]),
    _sama("praharshini", "praharṣiṇī", 13, "mnjrG"),
    _sama("manjubhashini", "mañjubhāṣiṇī", 13, "sjsjG", ["sunandinī", "prabodhitā"]),
    _sama("mattamayura", "mattamayūra", 13, "mtysG"),
    _sama("rucira", "rucirā", 13, "jbsjG", ["prabhāvatī"]),

    _sama("aparajita", "aparājitā", 14, "nnrsLG"),
    _sama("asambadha", "asaṃbādhā", 14, "mtnsGG"),
    _sama("pathya", "pathyā", 14, "sjsyLG", ["mañjarī"]),
    _sama("pramada", "pramadā", 14, "njbjLG", ["kurarīrutā"]),
    _sama("praharanakalika", "praharaṇakalikā", 14, "nnbnLG"),
    _sama("madhyakshama", "madhyakṣāmā", 14, "mbnyGG", ["haṃsaśyenī", "kuṭila"]),
    _sama("vasantatilaka", "vasantatilakā", 14, "tbjjGG"),
    _sama("vasanti", "vāsantī", 14, "mtnmGG"),

    _sama("carucamara", "cārucāmara", 15, "rjrjr", ["tūṇaka"]),
    _sama("malini", "mālinī", 15, "nnmyy"),
    _sama("lilakhela", "līlākhela", 15, "mmmmm"),
    _sama("shashikala", "śaśikalā", 15, "nnnns"),

    _sama("citra", "citra", 16, "rjrjrG"),
    _sama("pancacamara", "pañcacāmara", 16, "jrjrjG"),
    _sama("vanini", "vāṇinī", 16, "njbjrG"),

    _sama("citralekha-17", "citralekhā", 17, "ssjbjGG", ["atiśāyinī"]),
    _sama("narkutaka", "narkuṭaka", 17, "njbjjLG", ["nardaṭaka", "kokilaka"]),
    _sama("prthvi", "pṛthvī", 17, "jsjsyLG"),
    _sama("mandakranta", "mandākrāntā", 17, "mbnttGG", [], [4, 10]),
    _sama("vamsapatrapatita", "vaṃśapatrapatita", 17, "brnbnLG", ["vaṁśapatrapatita"]),
    _sama("shikharini", "śikhariṇī", 17, "ymnsbLG"),
    _sama("harini", "hariṇī", 17, "nsmrsLG"),

    _sama("kusumitalatavellita", "kusumitalatāvellitā", 18, "mtnyyy"),
    _sama("citralekha-18", "citralekhā", 18, "mbnyyy"),
    _sama("nandana", "nandana", 18, "njbjrr"),
    _sama("naraca", "nārāca", 18, "nnrrrr"),
    _sama("shardulalalita", "śārdūlalalita", 18, "msjsts"),
    _sama("mallikamala", "mallikāmālā", 18, "rsjjbr"),

    _sama("meghavispurjita", "meghavispūrjitā", 19, "ymnsrrG"),
    _sama("shardulavikridita", "śārdūlavikrīḍita", 19, "msjsttG", [], [12]),
    _sama("sumadhura", "sumadhurā", 19, "mrbnmnG"),
    _sama("surasa", "surasā", 19, "mrbnynG"),

    _sama("gitika", "gītikā", 20, "sjjbrsLG"),
    _sama("suvadana", "suvadanā", 20, "mrbnybLG"),

    _sama("pancakavali", "pañcakāvalī", 21, "njbjjjr", ["sarasī", "dhṛtaśrī"]),
    _sama("sragdhara", "sragdharā", 21, "mrbnyyy", [], [7, 14]),

    _sama("hamsi", "haṃsī", 22, "mmtnnnsG"),
    _sama("ashvadhati", "aśvadhāṭī", 22, "tbyjsrnG"),
    _sama("madraka", "madraka", 22, "brnrnrnG"),

    _sama("adritanaya", "adritanayā", 23, "njbjbjbLG"),
    _sama("shravanabharanam", "śravaṇābharaṇam", 23, "njjjjjjLG",
          ["virājitam", "śravaṇābharaṇa"]),

    _sama("tanvi", "tanvī", 24, "btnsbbny"),
    _sama("krauncapada", "krauñcapadā", 25, "bmsbnnnnG"),
    _sama("bhujangavijrmbhita", "bhujaṅgavijṛmbhita", 26, "mmtnnnrsLG"),
    _sama("shivatandava", "śivatāṇḍava", 26, "jsnbjsnbLG"),
)

ARDHASAMA_METERS: Tuple[ClassicalVarnaMeterSpec, ...] = (
    _ardhasama("upacitra", "upacitra", "sssLG", "bbbGG", 1),
    _ardhasama("vegavati", "vegavatī", "LLbbGG", "bbbGG", 2),
    _ardhasama("harinapluta", "hariṇaplutā", "LLbbr", "nbbr", 3),
    _ardhasama("malabharini", "mālābhāriṇī", "ssjGG", "sbry", 4, ["aupacchandasika"]),
    _ardhasama("drutamadhya", "drutamadhyā", "bbbGG", "njjy", 5),
    _ardhasama("bhadravirat", "bhadravirāṭ", "tjrG", "msjGG", 6),
    _ardhasama("ketumati", "ketumatī", "sjsG", "brnGG", 7),
    _ardhasama("akhyanaki", "ākhyānakī", "ttjGG", "jtjGG", 8),
    _ardhasama("viparitakhyanaki", "viparītākhyānakī", "jtjGG", "ttjGG", 9),
    _ardhasama("aparavaktra", "aparavaktra", "nnrLG", "njjr", 10, ["vaitālīya"]),
    _ardhasama("pushpitagra", "puṣpitāgrā", "nnry", "njjrG", 11, ["aupacchandasika"]),
    _ardhasama("sundari", "sundarī", "ssjG", "sbrLG", 12, ["viyoginī", "vaitālīya"]),
    _ardhasama("yavamati", "yavamatī", "rjrj", "jrjrG", 13),
)

_APIDA_8 = "nnGG"
_APIDA_12 = "nnnLGG"
_APIDA_16 = "nnnnLLGG"
_APIDA_20 = "nnnnnnGG"

VISAMA_METERS: Tuple[ClassicalVarnaMeterSpec, ...] = (
    _visama("udgata", "udgatā", ["sjsL", "nsjG", "bnbG", "sjsjG"], "v. 1"),
    _visama(
        "udgata-kvacit",
        "udgatā",
        ["sjsL", "nsjG", "bnjLG", "sjsjG"],
        "v. 1, explicitly permitted third-pāda variant",
        ["udgatā (kvacit)"],
    ),
    _visama("saurabhaka", "saurabhaka", ["sjsL", "nsjG", "rnbG", "sjsjG"], "v. 2"),
    _visama("lalita", "lalita", ["sjsL", "nsjG", "nnss", "sjsjG"], "v. 3"),
    _visama("apida", "āpīḍa", [_APIDA_8, _APIDA_12, _APIDA_16, _APIDA_20], "v. 2"),
    _visama("kalika", "kalikā", [_APIDA_12, _APIDA_8, _APIDA_16, _APIDA_20], "v. 3",
            ["mañjarī"]),
    _visama("lavali", "lavalī", [_APIDA_12, _APIDA_16, _APIDA_8, _APIDA_20], "v. 4"),
    _visama("amrtadhara", "amṛtadhārā",
            [_APIDA_12, _APIDA_16, _APIDA_20, _APIDA_8], "v. 5"),
    _visama(
        "upasthitapracupita",
        "upasthitapracupita",
        ["msjbGG", "snjrG", "nns", "nnnjy"],
        "v. 1",
    ),
    _visama("vardhamana", "vardhamāna",
            ["msjbGG", "snjrG", "nnsnns", "nnnjy"], "v. 2"),
    _visama(
        "shuddhaviradarsabha",
        "śuddhavirāḍārṣabha",
        ["msjbGG", "snjrG", "tjr", "nnnjy"],
        "v. 3",
    ),
)

DANDAKA_METERS: Tuple[ClassicalVarnaMeterSpec, ...] = (
    _repha_dandaka("candavrshtiprapata", "caṇḍavṛṣṭiprapāta", 7, "v. 176"),
    _repha_dandaka("arna", "arṇa", 8, "v. 177"),
    _repha_dandaka("arnava", "arṇava", 9, "v. 178"),
    _repha_dandaka("vyala", "vyāla", 10, "v. 179"),
    _repha_dandaka("jimuta", "jīmūta", 11, "v. 180"),
    _repha_dandaka("lilakara", "līlākara", 12, "v. 181"),
    _repha_dandaka("uddama", "uddāma", 13, "v. 182"),
    _repha_dandaka("shankha", "śaṅkha", 14, "v. 183"),
    _repha_dandaka("ambuja", "ambuja", 15, "commentary after vv. 177–183"),
    _dandaka("pracitaka", "pracitaka", "nn" + "y" * 7, "v. 184"),
)

#: Complete deterministic classical varṇa catalog currently supported.
CLASSICAL_VARNA_METERS: Tuple[ClassicalVarnaMeterSpec, ...] = (
    SAMA_METERS + ARDHASAMA_METERS + VISAMA_METERS + DANDAKA_METERS
)

_EXPECTED_FORMS: Dict[ClassicalVarnaMeterKind, int] = {
    "sama-vrtta": 1,
    "ardhasama-vrtta": 2,
    "visama-vrtta": 4,
    "dandaka": 1,
}

_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_yati(spec: ClassicalVarnaMeterSpec, errors: List[str]) -> None:
    if not spec.yati:
        return
    if len(spec.yati) != len(spec.pada_patterns):
        errors.append(f"{spec.id}: yati form count must equal pāda-pattern form count")
        return
    for form_index, positions in enumerate(spec.yati):
        previous = 0
        for position in positions:
            if not isinstance(position, int) or position <= previous:
                errors.append(
                    f"{spec.id}: yati positions for form {form_index + 1} must increase"
                )
            if position >= len(spec.pada_patterns[form_index]):
                errors.append(f"{spec.id}: yati cannot fall at or after the end of a pāda")
            previous = position


def _validate_pattern_form(
    spec: ClassicalVarnaMeterSpec, pattern: str, index: int, errors: List[str]
) -> None:
    if not re.fullmatch(r"[GL]+", pattern):
        errors.append(f"{spec.id}: patterns must contain only G/L")
    try:
        gana = spec.gana_patterns[index] if index < len(spec.gana_patterns) else ""
        if expand_gana_pattern(gana) != pattern:
            errors.append(
                f"{spec.id}: gaṇa form {index + 1} does not expand to its stored G/L pattern"
            )
    except ValueError:
        errors.append(f"{spec.id}: gaṇa form {index + 1} is invalid")


def _validate_pattern_shapes(spec: ClassicalVarnaMeterSpec, errors: List[str]) -> None:
    expected_forms = _EXPECTED_FORMS[spec.kind]
    if len(spec.gana_patterns) != expected_forms:
        errors.append(f"{spec.id}: {spec.kind} requires {expected_forms} gaṇa-pattern form(s)")
    if len(spec.pada_patterns) != expected_forms:
        errors.append(f"{spec.id}: {spec.kind} requires {expected_forms} pāda-pattern form(s)")
    for index, pattern in enumerate(spec.pada_patterns):
        _validate_pattern_form(spec, pattern, index, errors)


def _validate_catalog_entry(spec: ClassicalVarnaMeterSpec, errors: List[str]) -> None:
    if not _ID_PATTERN.match(spec.id):
        errors.append(f"{spec.id}: id must be lowercase ASCII kebab-case")
    if spec.name.strip() == "":
        errors.append(f"{spec.id}: name cannot be empty")
    if len(set(spec.aliases)) != len(spec.aliases):
        errors.append(f"{spec.id}: aliases must not repeat within one entry")
    _validate_pattern_shapes(spec, errors)
    if spec.source.work.strip() == "" or spec.source.locator.strip() == "":
        errors.append(f"{spec.id}: source work and locator are required")
    _validate_yati(spec, errors)


def validate_chandas_catalog(
    catalog: Sequence[ClassicalVarnaMeterSpec] = CLASSICAL_VARNA_METERS,
) -> ChandasCatalogValidation:
    """Validates identifiers, shapes, pattern alphabets, sources, and exact duplicates."""
    errors: List[str] = []
    ids = set()
    signatures: Dict[str, str] = {}
    for spec in catalog:
        _validate_catalog_entry(spec, errors)
        if spec.id in ids:
            errors.append(f"{spec.id}: duplicate id")
        ids.add(spec.id)
        signature = f"{spec.kind}:{'/'.join(spec.pada_patterns)}:{spec.terminal_policy}"
        previous = signatures.get(signature)
        if previous:
            errors.append(f"{spec.id}: exact pattern duplicates {previous}")
        else:
            signatures[signature] = spec.id
    return ChandasCatalogValidation(valid=not errors, errors=tuple(errors))


def meter_by_id(meter_id: str) -> Optional[ClassicalVarnaMeterSpec]:
    return next((spec for spec in CLASSICAL_VARNA_METERS if spec.id == meter_id), None)
