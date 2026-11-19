#!/usr/bin/env python3
"""Suivi de performances multiplateforme : TikTok et YouTube Shorts, toujours séparés.

Commandes :
  init     crée le CSV de suivi
  add      ajoute un clip (métadonnées communes)
  update   met à jour les stats d'UNE plateforme pour un clip
  report   rapport Markdown : stats par plateforme, meilleure plateforme, diagnostic croisé

Exemples :
  python3 tracker.py init
  python3 tracker.py add --id gta6-001 --name "Braquage raté" --streamer X \
      --source-url https://twitch.tv/videos/123 --timestamp 01:23:45-01:24:31 --type humour --duration 46
  python3 tracker.py update --id gta6-001 --platform tiktok --published 2026-11-20 \
      --views 48.2k --likes 5100 --comments 230 --shares 410 --retention 61
  python3 tracker.py update --id gta6-001 --platform youtube --published 2026-11-20 \
      --views 12900 --likes 880 --comments 41 --subs 37 --retention 74
  python3 tracker.py report --out rapport.md
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

COLUMNS = [
    "ID clip", "Nom du clip", "Streamer", "URL source", "Timestamp", "Type de moment", "Durée (s)",
    # --- TikTok
    "Date publication TikTok", "URL TikTok", "Vues TikTok", "Likes TikTok", "Commentaires TikTok",
    "Partages TikTok", "Rétention TikTok (%)", "Revenus TikTok",
    # --- YouTube Shorts
    "Date publication YouTube Shorts", "URL YouTube", "Vues YouTube", "Likes YouTube",
    "Commentaires YouTube", "Abonnés gagnés YouTube", "Rétention YouTube (%)", "Revenus YouTube",
    # --- Calculé
    "Performance globale", "Meilleure plateforme",
]

FIELDS = {
    "tiktok": {
        "published": "Date publication TikTok", "url": "URL TikTok", "views": "Vues TikTok",
        "likes": "Likes TikTok", "comments": "Commentaires TikTok", "shares": "Partages TikTok",
        "retention": "Rétention TikTok (%)", "revenue": "Revenus TikTok",
    },
    "youtube": {
        "published": "Date publication YouTube Shorts", "url": "URL YouTube", "views": "Vues YouTube",
        "likes": "Likes YouTube", "comments": "Commentaires YouTube", "subs": "Abonnés gagnés YouTube",
        "retention": "Rétention YouTube (%)", "revenue": "Revenus YouTube",
    },
}
LABEL = {"tiktok": "TikTok", "youtube": "YouTube Shorts"}
TIERS = [(100_000, "Viral"), (20_000, "Fort"), (3_000, "Moyen"), (0, "Faible")]


# ------------------------------------------------------------------ utilitaires
def num(v) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace(" ", "").replace(" ", "").replace("€", "").replace("$", "").replace("%", "")
    if not s:
        return None
    mult = 1
    if s[-1].lower() in "km":
        mult = 1_000 if s[-1].lower() == "k" else 1_000_000
        s = s[:-1]
    try:
        return float(s.replace(",", ".")) * mult
    except ValueError:
        return None


def pct(x: float | None, fmt: str = ".1%") -> str:
    return "—" if x is None else format(x, fmt)


def short(n: float | None) -> str:
    if n is None:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return f"{n:g}"


def load(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"{path} introuvable — lancer d'abord : tracker.py init")
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for c in COLUMNS:
            r.setdefault(c, "")
    return rows


def save(path: Path, rows: list[dict]) -> None:
    for r in rows:
        compute(r)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------------------------ scoring
def platform_stats(r: dict, p: str) -> dict | None:
    F = FIELDS[p]
    views = num(r[F["views"]])
    if not views:
        return None
    likes = num(r[F["likes"]]) or 0
    comments = num(r[F["comments"]]) or 0
    extra = num(r[F["shares"]]) or 0 if p == "tiktok" else 0
    subs = num(r[F["subs"]]) or 0 if p == "youtube" else 0
    eng = (likes + comments + extra) / views
    ret = num(r[F["retention"]])
    # Score de comparaison inter-plateformes : portée (log des vues) × engagement.
    # La rétention n'entre PAS dans le score : ses valeurs ne sont pas comparables entre
    # TikTok et Shorts. Elle est analysée séparément dans le diagnostic.
    score = math.log10(1 + views) * (1 + 2 * eng)
    if p == "youtube" and subs:
        score *= 1 + min(subs / views * 10, 0.1)  # petit bonus abonnés gagnés (max +10 %)
    return {"views": views, "likes": likes, "comments": comments, "shares": extra, "subs": subs,
            "eng": eng, "ret": ret, "score": score, "revenue": num(r[F["revenue"]])}


def compute(r: dict) -> None:
    st = {p: platform_stats(r, p) for p in FIELDS}
    live = {p: s for p, s in st.items() if s}
    if not live:
        r["Performance globale"] = ""
        r["Meilleure plateforme"] = ""
        return
    best_views = max(s["views"] for s in live.values())
    tier = next(label for threshold, label in TIERS if best_views >= threshold)
    r["Performance globale"] = tier
    if len(live) == 1:
        p = next(iter(live))
        r["Meilleure plateforme"] = f"{LABEL[p]} (seule publiée)"
        return
    a, b = st["tiktok"]["score"], st["youtube"]["score"]
    if abs(a - b) / max(a, b) < 0.08:
        r["Meilleure plateforme"] = "Équivalent"
    else:
        r["Meilleure plateforme"] = "TikTok" if a > b else "YouTube Shorts"


def diagnose(r: dict) -> list[str]:
    tt, yt = platform_stats(r, "tiktok"), platform_stats(r, "youtube")
    tips = []
    tier = r["Performance globale"]
    if tt and not yt and tier in ("Fort", "Viral"):
        tips.append("Fonctionne sur TikTok → à publier sur YouTube Shorts (titre recherchable, compréhensible sans son).")
    if yt and not tt and tier in ("Fort", "Viral"):
        tips.append("Fonctionne sur Shorts → à publier sur TikTok (hook plus émotionnel dès la 1re seconde).")
    if tt and yt:
        ratio = tt["views"] / yt["views"]
        if ratio >= 3:
            tips.append(f"TikTok ×{ratio:.1f} vs Shorts : retravailler le titre et la première frame YouTube, "
                        "vérifier que le payoff se comprend sans contexte, tester un autre horaire.")
        elif ratio <= 1 / 3:
            tips.append(f"Shorts ×{1 / ratio:.1f} vs TikTok : le hook TikTok accroche trop tard ou le ton est trop "
                        "« informatif » ; tester une ouverture plus émotionnelle / plus rapide.")
        if tt["eng"] >= 2 * yt["eng"] and yt["eng"] > 0:
            tips.append("Engagement TikTok bien supérieur : le moment suscite des réactions → poser une question en commentaire épinglé sur YouTube.")
    if tt and tt["ret"] is not None and tt["ret"] < 40:
        tips.append("Rétention TikTok < 40 % : le début est trop lent ou le hook ne tient pas sa promesse.")
    if yt and yt["ret"] is not None and yt["ret"] < 60:
        tips.append("Rétention Shorts < 60 % : clip probablement trop long pour le moment, ou début peu clair.")
    return tips


# ------------------------------------------------------------------ commandes
def cmd_init(a) -> None:
    p = Path(a.file)
    if p.exists() and not a.force:
        sys.exit(f"{p} existe déjà (--force pour recréer).")
    save(p, [])
    print(f"✓ {p} créé ({len(COLUMNS)} colonnes, TikTok et YouTube séparés).")


def cmd_add(a) -> None:
    p = Path(a.file)
    rows = load(p)
    if any(r["ID clip"] == a.id for r in rows):
        sys.exit(f"Le clip {a.id} existe déjà.")
    row = {c: "" for c in COLUMNS}
    row.update({"ID clip": a.id, "Nom du clip": a.name, "Streamer": a.streamer, "URL source": a.source_url,
                "Timestamp": a.timestamp, "Type de moment": a.type or "", "Durée (s)": a.duration or ""})
    rows.append(row)
    save(p, rows)
    print(f"✓ Clip {a.id} ajouté.")


def cmd_update(a) -> None:
    p = Path(a.file)
    rows = load(p)
    row = next((r for r in rows if r["ID clip"] == a.id), None)
    if not row:
        sys.exit(f"Clip {a.id} introuvable (utiliser add).")
    F = FIELDS[a.platform]
    if a.shares is not None and a.platform != "tiktok":
        sys.exit("--shares ne concerne que TikTok dans ce tableau.")
    if a.subs is not None and a.platform != "youtube":
        sys.exit("--subs (abonnés gagnés) ne concerne que YouTube.")
    changed = []
    for key in ("published", "url", "views", "likes", "comments", "shares", "subs", "retention", "revenue"):
        val = getattr(a, key, None)
        if val is None:
            continue
        if key not in ("published", "url"):
            n = num(val)
            if n is None:
                sys.exit(f"Valeur numérique invalide pour --{key} : {val!r}")
            val = f"{n:g}"
        row[F[key]] = val
        changed.append(F[key])
    save(p, rows)
    print(f"✓ {a.id} [{LABEL[a.platform]}] : {', '.join(changed) or 'rien'} → "
          f"{row['Performance globale'] or '—'} / meilleure : {row['Meilleure plateforme'] or '—'}")


def platform_totals(rows: list[dict], p: str) -> dict:
    s = [x for x in (platform_stats(r, p) for r in rows) if x]
    rets = [x["ret"] for x in s if x["ret"] is not None]
    revs = [x["revenue"] for x in s if x["revenue"] is not None]
    return {
        "n": len(s),
        "views": sum(x["views"] for x in s),
        "likes": sum(x["likes"] for x in s),
        "comments": sum(x["comments"] for x in s),
        "shares": sum(x["shares"] for x in s),
        "subs": sum(x["subs"] for x in s),
        "eng": (sum(x["eng"] for x in s) / len(s)) if s else None,
        "ret": (sum(rets) / len(rets)) if rets else None,
        "revenue": sum(revs) if revs else None,
    }


def group_table(rows: list[dict], key: str) -> list[str]:
    groups = defaultdict(list)
    for r in rows:
        groups[r[key] or "—"].append(r)
    out = [f"| {key} | Clips | Vues moy. TikTok | Vues moy. Shorts | Engag. TikTok | Engag. Shorts | Tendance |",
           "|---|---|---|---|---|---|---|"]
    for g, rs in sorted(groups.items()):
        t, y = platform_totals(rs, "tiktok"), platform_totals(rs, "youtube")
        tv = t["views"] / t["n"] if t["n"] else None
        yv = y["views"] / y["n"] if y["n"] else None
        trend = "—"
        if tv and yv:
            trend = "TikTok" if tv > yv * 1.2 else "Shorts" if yv > tv * 1.2 else "Équilibré"
        out.append(f"| {g} | {len(rs)} | {short(tv)} | {short(yv)} | "
                   f"{pct(t['eng'])} | "
                   f"{pct(y['eng'])} | {trend} |")
    return out


def cmd_report(a) -> None:
    rows = load(Path(a.file))
    for r in rows:
        compute(r)
    L = ["# Rapport de clipping — TikTok + YouTube Shorts", "",
         f"{len(rows)} clip(s) suivis. Les statistiques de chaque plateforme sont présentées séparément.", ""]

    L += ["## Totaux par plateforme", "",
          "| Plateforme | Clips publiés | Vues | Likes | Commentaires | Partages / Abonnés | Engag. moyen | Rétention moy. | Revenus |",
          "|---|---|---|---|---|---|---|---|---|"]
    for p in FIELDS:
        t = platform_totals(rows, p)
        extra = f"{short(t['shares'])} partages" if p == "tiktok" else f"{short(t['subs'])} abonnés"
        L.append(f"| {LABEL[p]} | {t['n']} | {short(t['views'])} | {short(t['likes'])} | {short(t['comments'])} | {extra} | "
                 f"{pct(t['eng'])} | "
                 f"{'—' if t['ret'] is None else f"{t['ret']:.0f} %"} | "
                 f"{'—' if t['revenue'] is None else f"{t['revenue']:.2f}"} |")

    L += ["", "## Par clip", "",
          "| Clip | Streamer | TikTok vues / likes / comm. / partages | Shorts vues / likes / comm. / abonnés | Rétention TT / YT | Performance | Meilleure |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        tt, yt = platform_stats(r, "tiktok"), platform_stats(r, "youtube")
        tts = f"{short(tt['views'])} / {short(tt['likes'])} / {short(tt['comments'])} / {short(tt['shares'])}" if tt else "non publié"
        yts = f"{short(yt['views'])} / {short(yt['likes'])} / {short(yt['comments'])} / {short(yt['subs'])}" if yt else "non publié"
        rt = ("—" if not tt or tt["ret"] is None else f"{tt['ret']:.0f}%") + " / " + ("—" if not yt or yt["ret"] is None else f"{yt['ret']:.0f}%")
        L.append(f"| {r['Nom du clip']} | {r['Streamer']} | {tts} | {yts} | {rt} | {r['Performance globale'] or '—'} | {r['Meilleure plateforme'] or '—'} |")

    L += ["", "## Diagnostic croisé (TikTok ↔ Shorts)", ""]
    any_tip = False
    for r in rows:
        tips = diagnose(r)
        if tips:
            any_tip = True
            L.append(f"**{r['Nom du clip']}** (`{r['ID clip']}`)")
            L += [f"- {t}" for t in tips]
            L.append("")
    if not any_tip:
        L += ["Pas assez de données pour un diagnostic croisé.", ""]

    L += ["## Par streamer", ""] + group_table(rows, "Streamer")
    L += ["", "## Par type de moment", ""] + group_table(rows, "Type de moment")
    L.append("")

    text = "\n".join(L)
    save(Path(a.file), rows)  # persiste Performance globale / Meilleure plateforme recalculées
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"✓ Rapport → {a.out}")
    else:
        print(text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default="tracker.csv", help="CSV de suivi (défaut : tracker.csv)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init")
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_init)

    ad = sub.add_parser("add")
    ad.add_argument("--id", required=True)
    ad.add_argument("--name", required=True)
    ad.add_argument("--streamer", required=True)
    ad.add_argument("--source-url", required=True)
    ad.add_argument("--timestamp", required=True)
    ad.add_argument("--type", help="humour, suspense, réaction, émotion, inattendu, skill…")
    ad.add_argument("--duration", help="Durée en secondes")
    ad.set_defaults(func=cmd_add)

    u = sub.add_parser("update")
    u.add_argument("--id", required=True)
    u.add_argument("--platform", required=True, choices=["tiktok", "youtube"])
    u.add_argument("--published", help="Date de publication (AAAA-MM-JJ)")
    u.add_argument("--url", help="URL du post")
    for k in ("views", "likes", "comments", "shares", "subs", "retention", "revenue"):
        u.add_argument(f"--{k}")
    u.set_defaults(func=cmd_update)

    r = sub.add_parser("report")
    r.add_argument("--out", help="Écrire le rapport dans un fichier .md")
    r.set_defaults(func=cmd_report)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
