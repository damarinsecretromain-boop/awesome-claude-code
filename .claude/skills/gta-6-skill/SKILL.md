---
name: gta-6-skill
description: Système de clipping multiplateforme TikTok + YouTube Shorts. Repère un moment viral dans un stream ou une VOD (GTA 6 et gaming en priorité), récupère le timestamp, monte un clip vertical 9:16 1080x1920 H.264 avec sous-titres et hook, prépare deux packs de publication distincts (TikTok et YouTube Shorts), suit les statistiques de chaque plateforme séparément et analyse les résultats pour améliorer les prochains clips. À utiliser dès que l'utilisateur parle de clip, clipping, Shorts, TikTok, hook, VOD, timestamp, stream, pack de publication ou suivi de performances de clips.
---

# GTA-6-SKILL — Clipping multiplateforme TikTok + YouTube Shorts

Ce skill gère une activité de clipping complète, pensée **dès le départ pour deux plateformes** :
TikTok **et** YouTube Shorts. Aucune plateforme n'est privilégiée : chaque clip vise les deux,
avec des stratégies, hooks, titres, descriptions et analyses adaptés à chacune.

```
Repérer un moment → timestamp → clip vertical 9:16 → sous-titres → hooks
→ pack TikTok + pack YouTube Shorts → publication → suivi séparé des stats
→ analyse → amélioration des prochains clips
```

Tous les chemins ci-dessous sont relatifs au dossier de ce skill (`.claude/skills/gta-6-skill/`).
Les clips produits vont dans un dossier de travail `clips/<id-clip>/` (à la racine du projet
de l'utilisateur, ou celui qu'il indique).

## Règles non négociables

1. **Deux plateformes, toujours.** Chaque moment retenu produit un pack TikTok **et** un pack
   YouTube Shorts. Jamais un système « TikTok seulement » ou « Shorts seulement ».
2. **Un seul moment par vidéo.** Pas de compilation, pas de mélange de moments sans rapport.
   Un clip = contexte compréhensible → accroche → progression → payoff (réaction, surprise,
   conclusion). Voir `references/selection-moments.md`.
3. **Format vertical** : 9:16, 1080×1920, MP4, H.264 + AAC, audio clair et synchronisé,
   sous-titres lisibles sur mobile, début immédiat, pas de temps mort.
4. **Durée = durée du moment.** Viser ~20–60 s quand le moment s'y prête, sans en faire une
   règle. Ne jamais rallonger artificiellement. Si l'histoire a besoin de plus, garder le temps
   nécessaire (au-delà de 3 min, prévenir : ce n'est plus publiable en Short).
5. **Statistiques jamais fusionnées.** TikTok et YouTube sont suivis dans des colonnes séparées.
6. **Pas de filigrane croisé.** Un export TikTok (avec logo TikTok) ne part jamais sur YouTube,
   et inversement. On exporte toujours depuis le master propre produit par `make_clip.py`.
7. **Pas de clickbait trompeur.** Le titre/hook promet ce que le clip montre réellement.
8. **Droits.** Ne clipper que des streamers qui l'autorisent (programme de clipping, accord,
   politique publique). Toujours créditer le streamer et la source. En cas de doute, le signaler.

## Workflow

### Étape 1 — Repérer le moment et le timestamp

Sources possibles : URL de VOD/stream (Twitch, YouTube, Kick), fichier local, transcription,
chat log, ou description de l'utilisateur.

- Si une transcription existe (ou peut être générée avec `scripts/subtitles.py transcribe`),
  chercher : pics de réaction (cris, rires, « NON ! », silence brutal), retournements, échecs
  spectaculaires, moments émotionnels, répliques drôles, découvertes (easter eggs, bugs).
- Si un chat log est disponible, les pics de messages/émotes signalent souvent le payoff :
  remonter de 10–40 s pour trouver le début du contexte.
- Noter pour chaque candidat : `début`, `fin`, `payoff à t=…`, résumé en une phrase,
  type (humour / suspense / réaction / émotion / inattendu / skill).
- Noter avec la grille de `references/selection-moments.md` et ne garder que les candidats
  qui ont **contexte + accroche + progression + payoff** dans un seul passage continu.

Présenter les candidats à l'utilisateur sous forme de tableau (rang, timestamps, type,
score TikTok, score Shorts, justification) avant de monter, sauf s'il a demandé l'automatique.

### Étape 2 — Monter le clip vertical

```bash
python3 scripts/make_clip.py \
  --source "<fichier ou URL>" --start 01:23:45 --end 01:24:31 \
  --out clips/<id>/master.mp4 --mode blur \
  --subs clips/<id>/subs.ass --hook "Il pensait que personne ne le voyait…"
```

- `--mode blur` (défaut) : vidéo 16:9 centrée sur fond flouté — sûr pour du gameplay.
- `--mode crop` : recadrage plein écran (`--crop-x 0.5` = centre, 0 = gauche, 1 = droite) —
  idéal quand l'action ou la facecam est concentrée.
- `--mode facecam` : facecam en haut + gameplay en bas (donner `--cam x,y,w,h` en pixels source).
- L'URL nécessite `yt-dlp` ; sans lui, demander un fichier local.
- Le script applique : H.264 High, yuv420p, 30 fps, CRF 20, AAC 48 kHz, normalisation
  audio (-14 LUFS, adaptée au mobile), `+faststart`.
- Couper au plus serré : entrer **dans** l'action (≤ 1 s avant la première phrase utile),
  sortir **juste après** le payoff (0,5–1,5 s de réaction max).

### Étape 3 — Sous-titres

```bash
# Transcription (faster-whisper si installé), mots horodatés
python3 scripts/subtitles.py transcribe clips/<id>/master_raw.mp4 --out clips/<id>/words.json --lang fr
# Construction ASS mobile (2–4 mots par ligne, gros, contour noir, zone sûre) + SRT
python3 scripts/subtitles.py build --words clips/<id>/words.json --out clips/<id>/subs.ass --srt clips/<id>/subs.srt
# Ou à partir d'un SRT de la VOD entière, recalé sur le clip :
python3 scripts/subtitles.py build --srt-in vod.srt --offset 01:23:45 --duration 46 --out clips/<id>/subs.ass
```

Ordre conseillé : monter d'abord sans sous-titres (`master_raw.mp4`), transcrire, relire et
corriger la transcription (noms propres, argot, termes GTA), puis remonter avec `--subs`.
Les sous-titres restent dans la zone sûre commune aux deux plateformes (ni sous l'interface
du bas, ni sous la colonne d'icônes de droite).

### Étape 4 — Hooks

Générer **3 à 5 hooks** par clip puis choisir :
- un **hook écran** (≤ 7 mots idéalement, ≤ 45 caractères) affiché pendant ~2–3 s ;
- une variante TikTok (curiosité, émotion, ton parlé) et une variante Shorts (claire,
  compréhensible sans son, compatible avec un titre recherchable).
Voir `references/hooks.md`. Le hook ne spoile pas le payoff et ne ment pas.

### Étape 5 — Packs de publication (TikTok + YouTube Shorts)

```bash
python3 scripts/publish_pack.py init --id <id> --name "<nom du clip>" --streamer "<streamer>" \
  --source-url "<url>" --timestamp "01:23:45-01:24:31" --dir clips/<id>
```

Puis remplir `clips/<id>/pack.json` (voir `templates/pack.example.json`) avec :

**PACK TIKTOK** — hook écran, sous-titres (fichier), description courte, 3–5 hashtags
pertinents, suggestion de couverture (frame + texte), moment de publication (si données),
CTA naturel facultatif. Détails : `references/tiktok.md`.

**PACK YOUTUBE SHORTS** — 3 titres, titre recommandé, description YouTube (contexte + crédit
source + hashtags), 1–3 hashtags, mots-clés utiles, suggestion de couverture / première frame,
CTA adapté YouTube, catégorie (souvent « Jeux vidéo ») et playlist recommandée.
Détails : `references/youtube-shorts.md`.

Valider puis générer la fiche lisible :

```bash
python3 scripts/publish_pack.py validate clips/<id>/pack.json
python3 scripts/publish_pack.py render   clips/<id>/pack.json   # → pack.md
```

Le validateur bloque : hashtags d'une plateforme sur l'autre (#shorts sur TikTok, #fyp sur
YouTube), mention de l'autre plateforme, titre > 100 caractères, crédit source absent, etc.

### Étape 6 — Publication

- Publier le **même moment original** sur les deux plateformes, chacune avec son pack.
- Uploader `master.mp4` (sans filigrane) sur les deux. Ne jamais télécharger une vidéo
  TikTok pour la reposter sur YouTube (ou l'inverse).
- Si un connecteur de publication est disponible dans la session (Composio, Zapier, API
  officielle), proposer de publier mais **demander confirmation avant chaque publication** :
  c'est une action publique. Sinon, fournir le pack prêt à copier-coller.
- Enregistrer les dates de publication dans le tracker.

### Étape 7 — Suivi des performances (séparé par plateforme)

```bash
python3 scripts/tracker.py init                       # crée tracker.csv
python3 scripts/tracker.py add --id <id> --name "<nom>" --streamer "<s>" \
  --source-url "<url>" --timestamp "01:23:45-01:24:31"
python3 scripts/tracker.py update --id <id> --platform tiktok \
  --published 2026-11-20 --views 48200 --likes 5100 --comments 230 --shares 410 --retention 61
python3 scripts/tracker.py update --id <id> --platform youtube \
  --published 2026-11-20 --views 12900 --likes 880 --comments 41 --subs 37 --retention 74
python3 scripts/tracker.py report --out rapport.md
```

Le tracker conserve les colonnes demandées (nom, streamer, URL source, timestamp, dates de
publication TikTok/YouTube, vues/likes/commentaires/partages TikTok, vues/likes/commentaires/
abonnés gagnés YouTube, revenus TikTok/YouTube, performance globale, meilleure plateforme),
plus rétention par plateforme et URLs des posts. `Performance globale` et `Meilleure
plateforme` sont recalculées automatiquement à chaque `update`/`report`.

Les données viennent de l'utilisateur (TikTok Studio, YouTube Studio), d'un export CSV, ou
d'un connecteur si disponible. Ne jamais inventer de chiffres : un champ inconnu reste vide.
Le CSV s'importe tel quel dans Google Sheets si l'utilisateur préfère un tableur partagé.

### Étape 8 — Analyse et amélioration

`tracker.py report` produit :
- le tableau par clip avec stats TikTok et YouTube côte à côte (jamais additionnées) ;
- les totaux **par plateforme** ;
- pour chaque clip, la meilleure plateforme et un diagnostic croisé :
  « fonctionne sur TikTok → à tester sur Shorts » (et inversement), écart de vues,
  écart d'engagement, rétention faible propre à chaque plateforme ;
- les tendances par streamer et par type de moment.

À partir du rapport, rédiger des recommandations concrètes (voir `references/analyse.md`) :
types de moments à privilégier par plateforme, longueur idéale observée, hooks gagnants,
heures de publication, clips à republier ou à retravailler.

## Stratégie de republication (résumé)

Voir `references/republication.md`. Même moment original ; titre, description, hashtags et
hook adaptés ; aucun filigrane étranger ; règles de chaque plateforme respectées ; analyse
indépendante. Un clip performant sur une plateforme est candidat à l'autre si : rétention
élevée, payoff compréhensible sans son (pour Shorts) ou ton émotionnel fort (pour TikTok).

## Livrables par clip

```
clips/<id>/
  master.mp4      # 1080x1920 H.264/AAC, sans filigrane, pour les deux plateformes
  subs.ass/.srt   # sous-titres (incrustés + fichier séparé)
  cover.jpg       # frame suggérée (optionnel : make_clip.py --cover <sec>)
  pack.json       # données des deux packs
  pack.md         # fiche prête à copier-coller : PACK TIKTOK + PACK YOUTUBE SHORTS
tracker.csv       # suivi multiplateforme
```

## Références

- `references/selection-moments.md` — grille de notation, règle « un seul moment ».
- `references/hooks.md` — formules de hooks par plateforme.
- `references/tiktok.md` — rétention, descriptions, hashtags, couverture, horaires.
- `references/youtube-shorts.md` — titres, descriptions, recherche, recommandations, métriques.
- `references/republication.md` — publier un même moment sur les deux plateformes.
- `references/analyse.md` — KPIs, diagnostic croisé, boucle d'amélioration.
