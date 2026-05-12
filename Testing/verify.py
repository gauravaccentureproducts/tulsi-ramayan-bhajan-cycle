#!/usr/bin/env python3
"""
Tulsi-Ramayan Bhajan Cycle - Automated test runner.

Runs the automatable subset of Test_Cases.txt against any kaand folder
under Tulsi/. Exits with code 1 if any BLOCKER fails.

Usage:
    python verify.py                    # all kaand folders
    python verify.py --kaand Balkand    # one kaand
"""

import argparse
import re
import sys
from pathlib import Path

# Force UTF-8 stdout so Devanagari can be printed on Windows (cp932 default).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ----- Paths -----
SCRIPT_DIR = Path(__file__).resolve().parent          # Tulsi/Testing
TULSI_DIR = SCRIPT_DIR.parent                          # Tulsi

# ----- Severity -----
BLOCKER, MAJOR, MINOR = "BLOCKER", "MAJOR", "MINOR"

# ----- Mandatory voice descriptor phrases (TC-X-002) -----
VOICE_DESCRIPTOR_PHRASES = [
    "warm soulful male baritone",
    "slightly nasal resonance",
    "plaintive heart-tugging timbre",
    "restrained vibrato",
    "mid-to-low range",
    "vintage Hindi film bhajan playback style",
    "kathavachak",
]

# ----- Banned artist/label names (TC-X-001) -----
BANNED_NAMES = [
    "mukesh", "lata mangeshkar", "rafi", "mohammed rafi",
    "hmv", "saregama", "manna dey", "narendra sharma",
    "c. ramchandra", "ramchandra (composer)", "bharat vyas",
    "kavi pradeep", "shailendra", "hasrat jaipuri", "sahir",
    "majrooh", "naushad", "shankar jaikishan", "talat mahmood",
    "kishore kumar", "hemant kumar",
]

# ----- Banned filler/coined words (TC-F-007, TC-L-003) -----
BANNED_FILLERS = [
    "ललाम",
    "हुई हृदय की पाँव",
    "शाप-दुख-धारि",
    "दुष्ट-कमान",
    "विवाह-गान",
    "कौसल्या सुलक्षणा",
]

# ----- Stock-word frequency caps per chapter (TC-L-004) -----
STOCK_WORD_CAPS = {
    "महान":      6,
    "अभिराम":    5,
    "जय-जयकार":  4,
    "धाम":       8,
    "नाम":       8,
    "गान":       8,
}

# ----- Anchor raag per kaand (TC-C-003) -----
ANCHOR_RAAG = {
    "Balkand":        ["Yaman"],
    "Ayodhyakand":    ["Bhairav", "Puriya Dhanashri"],
    "Aranyakand":     ["Malkauns", "Bhopali"],
    "Kishkindhakand": ["Pahadi", "Brindavani Sarang", "Sarang"],
    "Sundarkand":     ["Hamir", "Bhairavi"],
    "Lankakand":      ["Marwa", "Adana", "Shree"],
    "Uttarkand":      ["Yaman", "Bhupali"],
}


# ================================================================
# Helpers
# ================================================================

class TestResult:
    __slots__ = ("tc_id", "title", "severity", "passed", "message")
    def __init__(self, tc_id, title, severity, passed, message=""):
        self.tc_id, self.title, self.severity = tc_id, title, severity
        self.passed, self.message = passed, message


def parse_chapter_file(path):
    """Return (style_block, lyrics_block, raw_text) or (None, None, raw)."""
    raw = path.read_text(encoding="utf-8")
    si = raw.find("========== STYLE")
    li = raw.find("========== LYRICS")
    if si < 0 or li < 0 or si >= li:
        return None, None, raw
    style_end = raw.find("\n", si) + 1
    lyrics_start = raw.find("\n", li) + 1
    style = raw[style_end:li].strip()
    lyrics = raw[lyrics_start:].strip()
    return style, lyrics, raw


def extract_verses(lyrics):
    """Return dict of {verse_num: content_text} for [Verse N] blocks."""
    out = {}
    parts = re.split(r"\[Verse (\d+)\]\s*\n", lyrics)
    for i in range(1, len(parts), 2):
        try:
            n = int(parts[i])
            body = re.split(r"\n\[", parts[i + 1], maxsplit=1)[0].strip()
            out[n] = body
        except (ValueError, IndexError):
            pass
    return out


def extract_choruses(lyrics):
    """Return list of [Chorus] block contents."""
    out = []
    parts = re.split(r"\[Chorus\]\s*\n", lyrics)
    for chunk in parts[1:]:
        body = re.split(r"\n\[", chunk, maxsplit=1)[0].strip()
        out.append(body)
    return out


def lyric_lines(text):
    """Split text into non-empty, non-tag lines."""
    return [l.strip() for l in text.split("\n")
            if l.strip() and not l.strip().startswith("[")]


# ================================================================
# Tests - Structural (TC-S)
# ================================================================

def tc_s_001(kaand_dir):
    txts = list(kaand_dir.glob("*.txt"))
    others = [p for p in kaand_dir.iterdir()
              if p.is_file() and p.suffix != ".txt"]
    ok = len(txts) == 5 and not others
    return TestResult("TC-S-001", "Folder file count", BLOCKER, ok,
                      f"{len(txts)} .txt + {len(others)} others")


def tc_s_002(kaand_dir):
    name = kaand_dir.name
    pat = re.compile(rf"^{name}_Ch[1-5]_[A-Za-z][A-Za-z_]*\.txt$")
    bad = [f.name for f in kaand_dir.glob("*.txt") if not pat.match(f.name)]
    return TestResult("TC-S-002", "File naming pattern", BLOCKER, not bad,
                      "ok" if not bad else f"bad: {bad}")


def tc_s_003(raw):
    s = raw.count("========== STYLE")
    l = raw.count("========== LYRICS")
    return TestResult("TC-S-003", "STYLE/LYRICS markers", BLOCKER,
                      s == 1 and l == 1, f"STYLE={s}, LYRICS={l}")


def tc_s_004(style):
    return TestResult("TC-S-004", "Style prompt <= 1000 chars", BLOCKER,
                      len(style) <= 1000, f"{len(style)} chars")


def tc_s_005(lyrics):
    tags = re.findall(r"\[Verse (\d+)\]", lyrics)
    found = sorted({int(t) for t in tags})
    expected = list(range(1, 13))
    return TestResult("TC-S-005", "12 verses (1-12)", BLOCKER,
                      found == expected, f"found {found}")


def tc_s_006_007(lyrics):
    issues = []
    choruses = extract_choruses(lyrics)
    if not choruses:
        issues.append("no chorus block")
    else:
        n = len(lyric_lines(choruses[0]))
        if n != 3:
            issues.append(f"mukhda has {n} lines (expected 3)")
    for vn, body in sorted(extract_verses(lyrics).items()):
        n = len(lyric_lines(body))
        if n != 4:
            issues.append(f"verse {vn} has {n} lines")
    return TestResult("TC-S-006/007", "Mukhda 3 + each verse 4 lines",
                      BLOCKER, not issues,
                      "ok" if not issues else "; ".join(issues))


def tc_s_008(lyrics):
    v5 = lyrics.find("[Verse 5]")
    v9 = lyrics.find("[Verse 9]")
    chorus_pos = [m.start() for m in re.finditer(r"\[Chorus\]", lyrics)]
    near5 = any(0 < v5 - cp < 300 for cp in chorus_pos)
    near9 = any(0 < v9 - cp < 300 for cp in chorus_pos)
    return TestResult("TC-S-008", "Chorus return at V5 and V9", MAJOR,
                      near5 and near9, f"near V5={near5}, near V9={near9}")


def tc_s_009(lyrics):
    return TestResult("TC-S-009", "[Outro] tag present", MAJOR,
                      "[Outro]" in lyrics,
                      "ok" if "[Outro]" in lyrics else "missing")


def tc_s_010(path, lyrics):
    if "_Ch5_" not in path.name:
        return TestResult("TC-S-010", "Final-chapter extra chorus",
                          MINOR, True, "n/a")
    v12 = lyrics.find("[Verse 12]")
    outro = lyrics.find("[Outro]")
    chorus_pos = [m.start() for m in re.finditer(r"\[Chorus\]", lyrics)]
    extra = any(v12 < cp < outro for cp in chorus_pos)
    return TestResult("TC-S-010", "Final-chapter extra chorus", MINOR,
                      extra, "ok" if extra else "missing extra chorus")


# ================================================================
# Tests - Fact Validation (TC-F)
# ================================================================

def tc_f_001(lyrics):
    return TestResult("TC-F-001", "No yuga error (कलियुग)", BLOCKER,
                      "कलियुग" not in lyrics,
                      "clean" if "कलियुग" not in lyrics else "found कलियुग")


def tc_f_002(lyrics):
    combos = [("मक्खन", "लूट"), ("मक्खन", "चुरा"), ("मक्खन", "चोरी"),
              ("माखन", "लूट"), ("माखन", "चुरा"), ("माखन", "चोरी")]
    bad = []
    for line in lyrics.split("\n"):
        for a, b in combos:
            if a in line and b in line:
                bad.append(f"'{a}'+'{b}'")
                break
    return TestResult("TC-F-002", "No Krishna butter-stealing", BLOCKER,
                      not bad, "clean" if not bad else f"found {bad}")


def tc_f_003(lyrics):
    bad = "स्त्री-वध" in lyrics
    return TestResult("TC-F-003", "No Valmiki stri-vadh dilemma", MAJOR,
                      not bad, "clean" if not bad else "found स्त्री-वध")


def tc_f_004(path, lyrics):
    if not (path.name.startswith("Balkand_") and "_Ch4_" in path.name):
        return TestResult("TC-F-004", "Ahalya rejoins Gautama",
                          MAJOR, True, "n/a")
    has_pati = "पति" in lyrics
    has_gautam = "गौतम" in lyrics
    return TestResult("TC-F-004", "Ahalya rejoins Gautama", MAJOR,
                      has_pati and has_gautam,
                      f"पति={has_pati}, गौतम={has_gautam}")


def tc_f_005(path, lyrics):
    if not (path.name.startswith("Balkand_") and "_Ch1_" in path.name):
        return TestResult("TC-F-005", "Avatar-katha trio (Balkand Ch1)",
                          BLOCKER, True, "n/a")
    required = ["नारद", "मनु", "शतरूपा", "प्रतापभानु"]
    missing = [r for r in required if r not in lyrics]
    return TestResult("TC-F-005", "Avatar-katha trio", BLOCKER,
                      not missing,
                      "all present" if not missing else f"missing {missing}")


def tc_f_006(path, lyrics):
    if not (path.name.startswith("Balkand_") and "_Ch2_" in path.name):
        return TestResult("TC-F-006", "Sumitra from both queens",
                          MAJOR, True, "n/a")
    has = [t in lyrics for t in ["दोनों", "सुमित्रा", "भाग"]]
    return TestResult("TC-F-006", "Sumitra from both queens", MAJOR,
                      all(has),
                      f"दोनों={has[0]}, सुमित्रा={has[1]}, भाग={has[2]}")


def tc_f_007(lyrics):
    found = [w for w in BANNED_FILLERS if w in lyrics]
    return TestResult("TC-F-007", "No filler/coined words", MAJOR,
                      not found,
                      "clean" if not found else f"found {found}")


# ================================================================
# Tests - Lyricist (TC-L)
# ================================================================

def tc_l_002(lyrics):
    # Long vowel signs (matras) + independent long vowels + nasal +
    # semi-vowel glides which are sustainable in bhajan singing.
    long_vowels = ['ा', 'ी', 'ू', 'े', 'ो', 'ौ', 'ै', 'ं',
                   'आ', 'ई', 'ऊ', 'ए', 'ऐ', 'ओ', 'औ', 'ँ',
                   'य', 'व', 'र']
    weak = []
    for vn, body in extract_verses(lyrics).items():
        for ln in lyric_lines(body):
            tail = ln.rstrip("।॥. ,")
            if not tail:
                continue
            last3 = tail[-3:]
            if not any(v in last3 for v in long_vowels):
                weak.append(f"V{vn}: ...{tail[-12:]}")
    ok = len(weak) <= 2
    return TestResult("TC-L-002", "Long-vowel rhyme endings", MAJOR, ok,
                      "ok" if ok else f"weak ({len(weak)}): {weak[:2]}")


def tc_l_004(lyrics):
    bad = []
    for w, cap in STOCK_WORD_CAPS.items():
        c = lyrics.count(w)
        if c > cap:
            bad.append(f"{w}={c}>{cap}")
    return TestResult("TC-L-004", "Stock-word frequency cap", MINOR,
                      not bad, "ok" if not bad else "; ".join(bad))


def tc_l_010(lyrics):
    issues = []
    if "अनंग" in lyrics:
        issues.append("अनंग present - verify not used as 'humble'")
    if "ज़" in lyrics:
        issues.append("ज़ (nukta) found")
    return TestResult("TC-L-010", "Word-sense correctness", MAJOR,
                      not issues, "ok" if not issues else "; ".join(issues))


# ================================================================
# Tests - Music Director (TC-M)
# ================================================================

def tc_m_002(lyrics):
    astras = ["ब्रह्मास्त्र", "वरुणास्त्र", "अग्न्यास्त्र", "शिवशर"]
    bad = []
    for line in lyrics.split("\n"):
        if sum(1 for a in astras if a in line) >= 3:
            bad.append(line.strip()[:50])
    return TestResult("TC-M-002", "No astra-stacking compounds", MAJOR,
                      not bad,
                      "clean" if not bad else f"found stack: {bad[0]}")


def tc_m_003(lyrics):
    return TestResult("TC-M-003", "No ज़ (nukta)", MAJOR,
                      "ज़" not in lyrics,
                      "clean" if "ज़" not in lyrics else "found ज़")


def tc_m_006(style):
    raags = ["Yaman", "Bhairav", "Puriya", "Malkauns", "Bhopali",
             "Pahadi", "Sarang", "Hamir", "Bhairavi", "Marwa",
             "Adana", "Shree", "Bhupali"]
    raag_ok = any(r in style for r in raags)
    tempo_kw = ["vilambit", "kaharwa", "dadra", "medium", "brisk",
                "tempo", "alaap", "build"]
    tempo_ok = any(k in style.lower() for k in tempo_kw)
    return TestResult("TC-M-006", "Tempo and raag stated in style", MAJOR,
                      raag_ok and tempo_ok,
                      f"raag={raag_ok}, tempo={tempo_ok}")


# ================================================================
# Tests - Suno Format (TC-X)
# ================================================================

def tc_x_001(style):
    s = style.lower()
    found = [n for n in BANNED_NAMES if n in s]
    return TestResult("TC-X-001", "No artist names in style", BLOCKER,
                      not found, "clean" if not found else f"found {found}")


def tc_x_002(style):
    missing = [p for p in VOICE_DESCRIPTOR_PHRASES if p not in style]
    return TestResult("TC-X-002", "Voice descriptor present", BLOCKER,
                      not missing,
                      "complete" if not missing else f"missing {missing[:2]}")


def tc_x_003(lyrics):
    issues = []
    if re.search(r"^#+\s", lyrics, re.MULTILINE):
        issues.append("markdown headers")
    if re.search(r"^\d+\.\s", lyrics, re.MULTILINE):
        issues.append("numeric line prefixes")
    if "### चौपाई" in lyrics or "### मंगल" in lyrics:
        issues.append("Devanagari section labels")
    if "पंक्ति-सत्यापन" in lyrics:
        issues.append("line-count footer")
    # समर्पण as a HEADER (markdown or standalone block label), not as
    # a verse word (e.g., "पुत्र-समर्पण" is legitimate).
    if "### समर्पण" in lyrics or re.search(r"^समर्पण\s*$", lyrics, re.M):
        issues.append("समर्पण dedication block")
    return TestResult("TC-X-003", "No markdown/numbers in lyrics", BLOCKER,
                      not issues,
                      "clean" if not issues else "; ".join(issues))


def tc_x_004(lyrics):
    required = ["[Chorus]"] + [f"[Verse {i}]" for i in range(1, 13)] + ["[Outro]"]
    missing = [t for t in required if t not in lyrics]
    return TestResult("TC-X-004", "All structure tags present", BLOCKER,
                      not missing,
                      "complete" if not missing else f"missing {missing[:3]}")


def tc_x_005(lyrics):
    bad = []
    for m in re.finditer(r"\[([^\]]+)\]", lyrics):
        if re.search(r"[ऀ-ॿ]", m.group(1)):
            bad.append(f"[{m.group(1)}]")
    return TestResult("TC-X-005", "Tags in English only", MAJOR,
                      not bad,
                      "clean" if not bad else f"bad {bad[:3]}")


def tc_x_006(lyrics):
    cs = extract_choruses(lyrics)
    if not cs:
        return TestResult("TC-X-006", "Chorus repeats verbatim", MAJOR,
                          False, "no chorus")
    first = cs[0]
    ok = all(c == first for c in cs[1:])
    return TestResult("TC-X-006", "Chorus repeats verbatim", MAJOR, ok,
                      f"{len(cs)} blocks; identical={ok}")


def tc_x_009(raw):
    bad = []
    for ch in ["‘", "’"]:
        if ch in raw:
            bad.append(repr(ch))
    return TestResult("TC-X-009", "No smart single quotes", MINOR,
                      not bad, "clean" if not bad else f"found {bad}")


def tc_x_010(path):
    return TestResult("TC-X-010", "File extension .txt", BLOCKER,
                      path.suffix == ".txt", path.suffix)


def tc_x_011(raw):
    bad = []
    for ch in raw:
        cp = ord(ch)
        if ((0x1F300 <= cp <= 0x1FAFF) or
            (0x2600 <= cp <= 0x27BF) or
            (0x1F000 <= cp <= 0x1F02F)):
            bad.append(ch)
    return TestResult("TC-X-011", "No emojis", MAJOR,
                      not bad, "clean" if not bad else f"emoji {bad[:3]}")


# ================================================================
# Tests - Linguistic (TC-T)
# ================================================================

def tc_t_002(raw):
    bad = [c for c in ["“", "”", "‘", "’"] if c in raw]
    return TestResult("TC-T-002", "No smart quotes", MAJOR,
                      not bad,
                      "clean" if not bad else f"found {len(bad)} types")


def tc_t_003(raw):
    return TestResult("TC-T-003", "No ellipsis char", MINOR,
                      "…" not in raw,
                      "clean" if "…" not in raw else "found U+2026")


# ================================================================
# Tests - Cross-chapter (TC-C, folder-level)
# ================================================================

def tc_c_001(kaand_dir):
    issues = []
    for f in sorted(kaand_dir.glob("*.txt")):
        style, lyrics, _ = parse_chapter_file(f)
        if not lyrics:
            continue
        cs = extract_choruses(lyrics)
        if not cs:
            issues.append(f"{f.name}: no chorus")
            continue
        lines = lyric_lines(cs[0])
        if len(lines) < 3:
            issues.append(f"{f.name}: mukhda <3 lines")
            continue
        if "जय" not in lines[2] or "राम" not in lines[2]:
            issues.append(f"{f.name}: line 3 lacks jay-राम")
    return TestResult("TC-C-001", "Jay-ghosh binding across mukhdas",
                      MAJOR, not issues,
                      "all bound" if not issues else "; ".join(issues))


def tc_c_002(kaand_dir):
    phrase = VOICE_DESCRIPTOR_PHRASES[0]
    issues = []
    for f in sorted(kaand_dir.glob("*.txt")):
        style, _, _ = parse_chapter_file(f)
        if style and phrase not in style:
            issues.append(f"{f.name}")
    return TestResult("TC-C-002", "Voice descriptor consistent", MAJOR,
                      not issues,
                      "consistent" if not issues else f"missing in {issues}")


def tc_c_003(kaand_dir):
    expected = ANCHOR_RAAG.get(kaand_dir.name, [])
    if not expected:
        return TestResult("TC-C-003", "Anchor raag matches kaand",
                          MAJOR, True, "no expectation set")
    issues = []
    for f in sorted(kaand_dir.glob("*.txt")):
        style, _, _ = parse_chapter_file(f)
        if style and not any(r in style for r in expected):
            issues.append(f.name)
    return TestResult("TC-C-003", f"Anchor raag ({'/'.join(expected)})",
                      MAJOR, not issues,
                      "ok" if not issues else f"missing in {issues}")


# ================================================================
# Runner
# ================================================================

def run_chapter(path):
    style, lyrics, raw = parse_chapter_file(path)
    if not style or not lyrics:
        return [TestResult("TC-S-003", "STYLE/LYRICS markers",
                           BLOCKER, False, "cannot parse file")]
    return [
        tc_s_003(raw), tc_s_004(style), tc_s_005(lyrics),
        tc_s_006_007(lyrics), tc_s_008(lyrics), tc_s_009(lyrics),
        tc_s_010(path, lyrics),
        tc_f_001(lyrics), tc_f_002(lyrics), tc_f_003(lyrics),
        tc_f_004(path, lyrics), tc_f_005(path, lyrics),
        tc_f_006(path, lyrics), tc_f_007(lyrics),
        tc_l_002(lyrics), tc_l_004(lyrics), tc_l_010(lyrics),
        tc_m_002(lyrics), tc_m_003(lyrics), tc_m_006(style),
        tc_x_001(style), tc_x_002(style), tc_x_003(lyrics),
        tc_x_004(lyrics), tc_x_005(lyrics), tc_x_006(lyrics),
        tc_x_009(raw), tc_x_010(path), tc_x_011(raw),
        tc_t_002(raw), tc_t_003(raw),
    ]


def run_kaand(kaand_dir):
    folder_tests = [
        tc_s_001(kaand_dir), tc_s_002(kaand_dir),
        tc_c_001(kaand_dir), tc_c_002(kaand_dir), tc_c_003(kaand_dir),
    ]
    chapter_tests = {}
    for f in sorted(kaand_dir.glob("*.txt")):
        chapter_tests[f.name] = run_chapter(f)
    return folder_tests, chapter_tests


def print_kaand_report(kaand_name, folder_tests, chapter_tests):
    print()
    print("=" * 78)
    print(f"KAAND: {kaand_name}")
    print("=" * 78)
    total = passed = failed = blockers = 0

    def report(group_name, tests):
        nonlocal total, passed, failed, blockers
        print(f"\n[{group_name}]")
        for t in tests:
            total += 1
            sym = "[OK]" if t.passed else "[!!]"
            if t.passed:
                passed += 1
            else:
                failed += 1
                if t.severity == BLOCKER:
                    blockers += 1
            print(f"   {sym} {t.tc_id:14s} [{t.severity:7s}] "
                  f"{t.title:42s}  {t.message}")

    report(f"Folder-level for {kaand_name}", folder_tests)
    for name in sorted(chapter_tests):
        report(name, chapter_tests[name])

    print()
    print(f"   Summary: {passed}/{total} passed, {failed} failed, "
          f"{blockers} BLOCKER(s)")
    return blockers


def main():
    p = argparse.ArgumentParser(description="Tulsi Ramayan test runner")
    p.add_argument("--kaand", help="Specific kaand name (e.g., Balkand)")
    args = p.parse_args()

    if args.kaand:
        targets = [TULSI_DIR / args.kaand]
    else:
        targets = [d for d in TULSI_DIR.iterdir()
                   if d.is_dir() and d.name != "Testing"]

    if not targets:
        print(f"No kaand folders found under {TULSI_DIR}")
        return 1

    total_blockers = 0
    for kd in sorted(targets):
        if not kd.exists():
            print(f"Skipping {kd.name} (does not exist)")
            continue
        ft, ct = run_kaand(kd)
        total_blockers += print_kaand_report(kd.name, ft, ct)

    print()
    print("=" * 78)
    print(f"OVERALL: {total_blockers} BLOCKER failure(s) across all kaands")
    print("=" * 78)
    return 1 if total_blockers > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
