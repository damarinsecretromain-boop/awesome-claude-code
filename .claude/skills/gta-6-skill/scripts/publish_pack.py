#!/usr/bin/env python3
"""Packs de publication par clip : un PACK TIKTOK + un PACK YOUTUBE SHORTS.

Commandes :
  init      crée clips/<id>/pack.json (squelette des deux packs)
  validate  vérifie les règles de chaque plateforme (erreurs bloquantes + avertissements)
  render    génère pack.md, prêt à copier-coller

Exemples :
  python3 publish_pack.py init --id gta6-001 --name "Braquage raté" --streamer "X" \
      --source-url https://twitch.tv/videos/123 --timestamp 01:23:45-01:24:31 --dir clips/gta6-001
  python3 publish_pack.py validate clips/gta6-001/pack.json
  python3 publish_pack.py render clips/gta6-001/pack.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TIKTOK_ONLY_TAGS = {"fyp", "foryou", "foryoupage", "pourtoi", "fypシ", "tiktok", "tiktokgaming", "viraltiktok"}
YOUTUBE_ONLY_TAGS = {"shorts", "short", "youtubeshorts", "ytshorts", "youtube"}
HASHTAG_RE = re.compile(r"^#[\wÀ-ɏ]+$", re.UNICODE)


def skeleton(a) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "streamer": a.streamer,
        "source_url": a.source_url,
        "timestamp": a.timestamp,
        "duration_s": None,
        "moment": {"type": "", "summary": "", "context": "", "hook": "", "progression": "", "payoff": ""},
        "video": {"file": "master.mp4", "subtitles_burned": "subs.ass", "subtitles_file": "subs.srt"},
        "tiktok": {
            "hook_screen": "",
            "hook_variants": [],
            "subtitles": "Incrustés (subs.ass)",
            "description": "",
            "hashtags": [],
            "cover": {"frame_s": None, "text": ""},
            "publish_time": {"slot": "", "basis": "à définir (données insuffisantes)"},
            "cta": "",
        },
        "youtube_shorts": {
            "titles": ["", "", ""],
            "recommended_title": "",
            "hook_screen": "",
            "description": "",
            "hashtags": [],
            "keywords": [],
            "cover": {"frame_s": None, "text": ""},
            "cta": "",
            "category": "Jeux vidéo",
            "playlist": "",
            "publish_time": {"slot": "", "basis": "à définir (données insuffisantes)"},
        },
        "cross_platform": {"tiktok_potential": "", "shorts_potential": "", "notes": ""},
    }


def cmd_init(a) -> None:
    d = Path(a.dir)
    d.mkdir(parents=True, exist_ok=True)
    p = d / "pack.json"
    if p.exists() and not a.force:
        sys.exit(f"{p} existe déjà (utiliser --force pour écraser).")
    p.write_text(json.dumps(skeleton(a), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {p} — remplir les deux packs puis lancer validate.")


def _tags(lst) -> list[str]:
    return [t.strip() for t in (lst or []) if t and t.strip()]


def _norm(tag: str) -> str:
    return tag.lstrip("#").lower()


def validate(pack: dict) -> tuple[list[str], list[str]]:
    E, W = [], []
    for k in ("id", "name", "streamer", "source_url", "timestamp"):
        if not pack.get(k):
            E.append(f"Champ « {k} » manquant.")

    m = pack.get("moment", {})
    for k in ("context", "hook", "progression", "payoff"):
        if not m.get(k):
            W.append(f"Moment : « {k} » non renseigné — un clip doit raconter UN moment complet.")

    # ---------------- TikTok
    tt = pack.get("tiktok", {})
    hook = tt.get("hook_screen", "")
    if not hook:
        E.append("TikTok : hook écran manquant.")
    elif len(hook) > 80:
        E.append(f"TikTok : hook écran trop long ({len(hook)} car.), illisible en 2–3 s.")
    elif len(hook) > 45:
        W.append(f"TikTok : hook écran de {len(hook)} car. — viser ≤ 45.")
    desc = tt.get("description", "")
    if not desc:
        E.append("TikTok : description manquante.")
    elif len(desc) > 2200:
        E.append(f"TikTok : description de {len(desc)} car. — beaucoup trop longue.")
    elif len(desc) > 150:
        W.append(f"TikTok : description de {len(desc)} car. — viser une description courte (≤ 150).")
    if "youtube" in (desc + hook + tt.get("cta", "")).lower():
        E.append("TikTok : le pack mentionne YouTube.")
    if pack.get("streamer") and pack["streamer"].lower() not in desc.lower():
        W.append("TikTok : le streamer n'est pas crédité dans la description.")
    tags = _tags(tt.get("hashtags"))
    if not 3 <= len(tags) <= 5:
        W.append(f"TikTok : {len(tags)} hashtags — viser 3 à 5 pertinents.")
    for t in tags:
        if not HASHTAG_RE.match(t):
            E.append(f"TikTok : hashtag invalide « {t} ».")
        if _norm(t) in YOUTUBE_ONLY_TAGS:
            E.append(f"TikTok : hashtag propre à YouTube « {t} ».")
    if len({_norm(t) for t in tags}) != len(tags):
        W.append("TikTok : hashtags en double.")
    if tt.get("cover", {}).get("frame_s") is None:
        W.append("TikTok : pas de frame de couverture suggérée.")

    # ---------------- YouTube Shorts
    yt = pack.get("youtube_shorts", {})
    titles = [t for t in yt.get("titles", []) if t and t.strip()]
    if len(titles) != 3:
        E.append(f"YouTube : {len(titles)} titre(s) — il en faut exactement 3.")
    for t in titles:
        if len(t) > 100:
            E.append(f"YouTube : titre > 100 car. : « {t[:40]}… »")
        elif len(t) > 70:
            W.append(f"YouTube : titre de {len(t)} car., risque d'être tronqué : « {t[:40]}… »")
        if "tiktok" in t.lower():
            E.append("YouTube : un titre mentionne TikTok.")
    rec = yt.get("recommended_title", "")
    if not rec:
        E.append("YouTube : titre recommandé manquant.")
    elif rec not in titles:
        E.append("YouTube : le titre recommandé doit être l'un des 3 titres.")
    ydesc = yt.get("description", "")
    if not ydesc:
        E.append("YouTube : description manquante.")
    elif len(ydesc) > 5000:
        E.append(f"YouTube : description de {len(ydesc)} car. (> 5000).")
    if "tiktok" in (ydesc + yt.get("cta", "")).lower():
        E.append("YouTube : le pack mentionne TikTok.")
    credit = (pack.get("streamer") or "").lower()
    if ydesc and credit and credit not in ydesc.lower() and (pack.get("source_url") or "") not in ydesc:
        E.append("YouTube : la description doit créditer le streamer ou la source.")
    ytags = _tags(yt.get("hashtags"))
    if not ytags:
        W.append("YouTube : aucun hashtag.")
    if len(ytags) > 15:
        E.append(f"YouTube : {len(ytags)} hashtags (> 15, YouTube risque de tous les ignorer).")
    elif len(ytags) > 3:
        W.append(f"YouTube : {len(ytags)} hashtags — seuls 3 s'affichent, garder les 1–3 meilleurs.")
    for t in ytags:
        if not HASHTAG_RE.match(t):
            E.append(f"YouTube : hashtag invalide « {t} ».")
        if _norm(t) in TIKTOK_ONLY_TAGS:
            E.append(f"YouTube : hashtag propre à TikTok « {t} ».")
    if not yt.get("cta"):
        W.append("YouTube : pas de CTA (ex. s'abonner pour la suite).")
    if not yt.get("category"):
        W.append("YouTube : catégorie non renseignée.")
    if yt.get("cover", {}).get("frame_s") is None:
        W.append("YouTube : pas de première frame / couverture suggérée.")

    dur = pack.get("duration_s")
    if isinstance(dur, (int, float)) and dur > 180:
        E.append(f"Durée {dur}s > 180 s : non publiable en YouTube Short (OK TikTok).")
    return E, W


def cmd_validate(a) -> int:
    pack = json.loads(Path(a.pack).read_text(encoding="utf-8"))
    E, W = validate(pack)
    for e in E:
        print("✗", e)
    for w in W:
        print("⚠", w)
    if not E:
        print(f"✓ Pack valide ({len(W)} avertissement(s)).")
    return 1 if E else 0


def render(pack: dict) -> str:
    tt, yt, m = pack["tiktok"], pack["youtube_shorts"], pack.get("moment", {})
    L = [
        f"# {pack['name']} — `{pack['id']}`",
        "",
        f"- **Streamer** : {pack['streamer']}",
        f"- **Source** : {pack['source_url']}",
        f"- **Timestamp** : {pack['timestamp']}" + (f" ({pack['duration_s']} s)" if pack.get("duration_s") else ""),
        f"- **Fichier** : `{pack['video']['file']}` (1080×1920, H.264, sans filigrane — même fichier pour les deux plateformes)",
        "",
        "## Le moment",
        f"- Type : {m.get('type', '')}",
        f"- Contexte : {m.get('context', '')}",
        f"- Accroche : {m.get('hook', '')}",
        f"- Progression : {m.get('progression', '')}",
        f"- Payoff : {m.get('payoff', '')}",
        "",
        "---",
        "",
        "## PACK TIKTOK",
        "",
        f"**Hook écran** : {tt.get('hook_screen', '')}",
    ]
    if tt.get("hook_variants"):
        L += ["", "Variantes :"] + [f"- {h}" for h in tt["hook_variants"]]
    L += [
        "",
        f"**Sous-titres** : {tt.get('subtitles', '')}",
        "",
        "**Description** :",
        "```",
        f"{tt.get('description', '')} {' '.join(tt.get('hashtags', []))}".strip(),
        "```",
        f"**Hashtags** : {' '.join(tt.get('hashtags', []))}",
        f"**Couverture** : frame à {tt.get('cover', {}).get('frame_s')} s — texte : « {tt.get('cover', {}).get('text', '')} »",
        f"**Publication** : {tt.get('publish_time', {}).get('slot') or '—'} ({tt.get('publish_time', {}).get('basis', '')})",
        f"**CTA** : {tt.get('cta') or '—'}",
        "",
        "---",
        "",
        "## PACK YOUTUBE SHORTS",
        "",
        "**Titres proposés** :",
    ]
    for i, t in enumerate(yt.get("titles", []), 1):
        star = " ⭐ recommandé" if t == yt.get("recommended_title") else ""
        L.append(f"{i}. {t}{star}")
    L += [
        "",
        f"**Titre recommandé** : {yt.get('recommended_title', '')}",
    ]
    if yt.get("hook_screen"):
        L.append(f"**Hook écran (si différent)** : {yt['hook_screen']}")
    L += [
        "",
        "**Description** :",
        "```",
        yt.get("description", ""),
        "```",
        f"**Hashtags** : {' '.join(yt.get('hashtags', []))}",
        f"**Mots-clés** : {', '.join(yt.get('keywords', [])) or '—'}",
        f"**Couverture / première frame** : frame à {yt.get('cover', {}).get('frame_s')} s — texte : « {yt.get('cover', {}).get('text', '')} »",
        f"**CTA** : {yt.get('cta') or '—'}",
        f"**Catégorie** : {yt.get('category') or '—'}  ·  **Playlist** : {yt.get('playlist') or '—'}",
        f"**Publication** : {yt.get('publish_time', {}).get('slot') or '—'} ({yt.get('publish_time', {}).get('basis', '')})",
        "",
        "---",
        "",
        "## Potentiel croisé",
        f"- TikTok : {pack.get('cross_platform', {}).get('tiktok_potential', '')}",
        f"- Shorts : {pack.get('cross_platform', {}).get('shorts_potential', '')}",
        f"- Notes : {pack.get('cross_platform', {}).get('notes', '')}",
        "",
    ]
    return "\n".join(L)


def cmd_render(a) -> None:
    p = Path(a.pack)
    pack = json.loads(p.read_text(encoding="utf-8"))
    E, W = validate(pack)
    if E and not a.force:
        for e in E:
            print("✗", e)
        sys.exit("Pack invalide — corriger ou utiliser --force.")
    out = Path(a.out) if a.out else p.with_name("pack.md")
    out.write_text(render(pack), encoding="utf-8")
    print(f"✓ {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    for k in ("id", "name", "streamer", "source-url", "timestamp"):
        i.add_argument(f"--{k}", required=True)
    i.add_argument("--dir", required=True)
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_init)
    v = sub.add_parser("validate")
    v.add_argument("pack")
    v.set_defaults(func=cmd_validate)
    r = sub.add_parser("render")
    r.add_argument("pack")
    r.add_argument("--out")
    r.add_argument("--force", action="store_true")
    r.set_defaults(func=cmd_render)
    a = ap.parse_args()
    rc = a.func(a)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
