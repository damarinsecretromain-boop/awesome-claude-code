#!/usr/bin/env python3
"""Sous-titres lisibles sur mobile pour clips verticaux (TikTok + YouTube Shorts).

Commandes :
  transcribe  vidéo → words.json (mots horodatés, via faster-whisper si installé)
  build       words.json ou SRT → .ass stylé (2–4 mots/ligne, zone sûre) + .srt optionnel

Exemples :
  python3 subtitles.py transcribe clip.mp4 --out words.json --lang fr
  python3 subtitles.py build --words words.json --out subs.ass --srt subs.srt
  python3 subtitles.py build --srt-in vod.srt --offset 01:23:45 --duration 46 --out subs.ass
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Zone sûre commune TikTok / Shorts sur 1080x1920 : éviter ~bas 20 % (légende, boutons)
# et la colonne d'icônes à droite. Texte centré, légèrement sous le milieu.
STYLE = {
    "font": "DejaVu Sans",
    "size": 82,
    "margin_v": 620,   # distance depuis le bas
    "margin_l": 90,
    "margin_r": 170,   # marge plus grande à droite (icônes)
    "outline": 6,
}
HIGHLIGHT = "&H0000E5FF"  # jaune (BGR) pour le mot accentué


def parse_time(value: str) -> float:
    total = 0.0
    for p in value.strip().replace(",", ".").split(":"):
        total = total * 60 + float(p)
    return total


def ass_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def srt_time(t: float) -> str:
    t = max(0.0, t)
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# --------------------------------------------------------------------- transcribe
def cmd_transcribe(args) -> None:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        sys.exit(
            "faster-whisper n'est pas installé : pip install faster-whisper\n"
            "Alternative : fournir un SRT existant (build --srt-in) ou une transcription."
        )
    model = WhisperModel(args.model, device="auto", compute_type="auto")
    segments, _ = model.transcribe(args.video, language=args.lang, word_timestamps=True, vad_filter=True)
    words = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append({"start": round(w.start, 3), "end": round(w.end, 3), "text": text})
    Path(args.out).write_text(json.dumps(words, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ {len(words)} mots → {args.out} (relire et corriger noms propres / argot avant build)")


# --------------------------------------------------------------------- build
def read_srt(path: str) -> list[dict]:
    blocks = re.split(r"\n\s*\n", Path(path).read_text(encoding="utf-8-sig").strip())
    cues = []
    for b in blocks:
        lines = [l for l in b.splitlines() if l.strip()]
        idx = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if idx is None:
            continue
        a, z = [x.strip().split(" ")[0] for x in lines[idx].split("-->")]
        cues.append({"start": parse_time(a), "end": parse_time(z), "text": " ".join(lines[idx + 1:])})
    return cues


def cues_to_words(cues: list[dict]) -> list[dict]:
    """Répartit linéairement chaque réplique SRT en mots (approximation)."""
    words = []
    for c in cues:
        toks = re.sub(r"<[^>]+>", "", c["text"]).split()
        if not toks:
            continue
        step = (c["end"] - c["start"]) / len(toks)
        for i, t in enumerate(toks):
            words.append({"start": c["start"] + i * step, "end": c["start"] + (i + 1) * step, "text": t})
    return words


def chunk(words: list[dict], max_words: int, max_chars: int, max_gap: float) -> list[dict]:
    lines, cur = [], []
    for w in words:
        text_len = sum(len(x["text"]) + 1 for x in cur) + len(w["text"])
        gap = w["start"] - cur[-1]["end"] if cur else 0
        ends_sentence = bool(cur) and cur[-1]["text"][-1:] in ".!?…"
        if cur and (len(cur) >= max_words or text_len > max_chars or gap > max_gap or ends_sentence):
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    out = []
    for i, ln in enumerate(lines):
        start = ln[0]["start"]
        end = ln[-1]["end"]
        nxt = lines[i + 1][0]["start"] if i + 1 < len(lines) else end + 0.6
        end = min(max(end, start + 0.45), nxt)  # durée mini lisible, sans chevauchement
        out.append({"start": start, "end": end, "words": ln})
    return out


def ass_text(line: dict, emphasize: set[str], upper: bool) -> str:
    parts = []
    for w in line["words"]:
        t = w["text"].upper() if upper else w["text"]
        t = t.replace("{", "(").replace("}", ")")
        key = re.sub(r"\W", "", w["text"]).lower()
        if key and key in emphasize:
            t = f"{{\\c{HIGHLIGHT}}}{t}{{\\c&H00FFFFFF&}}"
        parts.append(t)
    return " ".join(parts)


def write_ass(lines: list[dict], out: Path, emphasize: set[str], upper: bool) -> None:
    s = STYLE
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "WrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Sub,{s['font']},{s['size']},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,{s['outline']},2,2,{s['margin_l']},{s['margin_r']},{s['margin_v']},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    body = "".join(
        f"Dialogue: 0,{ass_time(l['start'])},{ass_time(l['end'])},Sub,,0,0,0,,"
        f"{{\\fscx92\\fscy92\\t(0,90,\\fscx100\\fscy100)}}{ass_text(l, emphasize, upper)}\n"
        for l in lines
    )
    out.write_text(header + body, encoding="utf-8")


def write_srt(lines: list[dict], out: Path) -> None:
    out.write_text(
        "\n".join(
            f"{i}\n{srt_time(l['start'])} --> {srt_time(l['end'])}\n"
            f"{' '.join(w['text'] for w in l['words'])}\n"
            for i, l in enumerate(lines, 1)
        ),
        encoding="utf-8",
    )


def cmd_build(args) -> None:
    if args.words:
        words = json.loads(Path(args.words).read_text(encoding="utf-8"))
    elif args.srt_in:
        words = cues_to_words(read_srt(args.srt_in))
    else:
        sys.exit("Fournir --words ou --srt-in.")

    offset = parse_time(args.offset) if args.offset else 0.0
    duration = float(args.duration) if args.duration else None
    shifted = []
    for w in words:
        st, en = w["start"] - offset, w["end"] - offset
        if en <= 0 or (duration is not None and st >= duration):
            continue
        shifted.append({"start": max(0.0, st), "end": en if duration is None else min(en, duration), "text": w["text"]})
    if not shifted:
        sys.exit("Aucun mot dans la fenêtre demandée (vérifier --offset / --duration).")

    lines = chunk(shifted, args.max_words, args.max_chars, args.max_gap)
    emphasize = {re.sub(r"\W", "", e).lower() for e in (args.emphasize or "").split(",") if e.strip()}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_ass(lines, out, emphasize, args.upper)
    print(f"✓ {len(lines)} lignes → {out}")
    if args.srt:
        write_srt(lines, Path(args.srt))
        print(f"✓ SRT → {args.srt}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("transcribe")
    t.add_argument("video")
    t.add_argument("--out", required=True)
    t.add_argument("--lang", default=None, help="fr, en… (auto si absent)")
    t.add_argument("--model", default="small")
    t.set_defaults(func=cmd_transcribe)

    b = sub.add_parser("build")
    b.add_argument("--words", help="words.json (transcribe)")
    b.add_argument("--srt-in", help="SRT source (ex. VOD entière)")
    b.add_argument("--offset", help="Début du clip dans la source (s ou HH:MM:SS)")
    b.add_argument("--duration", help="Durée du clip en secondes")
    b.add_argument("--out", required=True, help="Fichier .ass")
    b.add_argument("--srt", help="Exporter aussi un .srt")
    b.add_argument("--max-words", type=int, default=4)
    b.add_argument("--max-chars", type=int, default=22)
    b.add_argument("--max-gap", type=float, default=0.6)
    b.add_argument("--emphasize", help="Mots à surligner en jaune, séparés par des virgules")
    b.add_argument("--upper", action="store_true", help="Tout en majuscules")
    b.set_defaults(func=cmd_build)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
