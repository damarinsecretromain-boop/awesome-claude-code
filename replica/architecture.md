# Architecture : ton studio vidéo IA (reconstruction des fonctions de base de TrendStory)

Pour un usage interne : un ou quelques utilisateurs, aucune facturation, mais
chaque appel aux API d'IA est chiffré et journalisé. Source : `recon.md` et
`features.csv`.

## Stack

| couche | choix | pourquoi |
| --- | --- | --- |
| web | Next.js (App Router) + TypeScript | un seul dépôt pour l'interface et les actions serveur ; le SDK Anthropic TypeScript et les SDK des fournisseurs y sont de première classe |
| styles | Tailwind, tokens issus de `/replica-design` | rapide, cohérent |
| base de données | Postgres sur Supabase | Auth, RLS et Realtime au même endroit ; offre gratuite suffisante pour un usage interne |
| ORM | Drizzle | SQL lisible, types générés depuis `schema.sql` |
| auth | Supabase Auth (Google + lien magique) | rien à coder ; `auth.uid()` alimente directement la RLS |
| paiements | aucun | usage interne ; remplacés par un budget mensuel et un journal des coûts |
| email | aucun en plus | les emails de connexion de Supabase suffisent |
| jobs | Trigger.dev | tâches longues sans limite de temps, étapes relançables, extension ffmpeg, suivi de progression en direct côté client. Une vidéo, c'est 5 à 15 minutes de calcul : impossible dans une fonction Vercel |
| fichiers | Cloudflare R2 | les vidéos pèsent lourd et R2 ne facture pas la bande passante sortante ; URL signées pour le lecteur et le téléchargement |
| hébergement | Vercel (web) + Trigger.dev Cloud (worker) | aucun serveur à gérer |
| LLM | API Claude, `claude-opus-5-5` | script, découpage en scènes (sortie structurée), agent avec outils, résumé de l'histoire |
| images | Gemini API (Nano Banana) ; fal.ai pour les autres modèles | images de référence en entrée : c'est ce qui garde les personnages cohérents |
| vidéo | Gemini API (Veo 3.1) ; fal.ai pour Seedance, Grok Imagine, etc. | image → vidéo ; une seule clé fal donne accès à plusieurs modèles via leurs licences officielles |
| voix + musique | ElevenLabs (TTS avec horodatage, API musique) | l'horodatage mot à mot donne les sous-titres sans transcription séparée ; musique générée donc sous licence claire |
| montage | ffmpeg dans le worker | concaténation, mixage voix + musique, sous-titres ASS incrustés, export 9:16 ou 16:9 |

Uniquement des API officielles avec tes propres clés. Aucun appel aux points
d'accès privés de TrendStory. La disponibilité exacte de chaque modèle vidéo
(Veo 3.1, Seedance 2, Grok Imagine) et ses tarifs sont à **vérifier au jalon 1** :
ils changent vite.

### Claude : réglages

- `claude-opus-5-5` partout, avec le paramètre `effort` dans `output_config` :
  `medium` pour le script, `low` pour le résumé d'histoire, `high` pour l'agent.
  Opus 5.5 ne permet pas de désactiver la réflexion : c'est l'`effort` qui règle
  coût et profondeur.
- **Script** : sortie structurée (`output_config.format`) avec un schéma JSON
  `{title, scenes: [{narration, dialogue[], image_prompt, motion_prompt,
  duration_s, character_ids[]}]}`. Le résultat va tel quel dans `projects.script`.
- **Agent** : boucle d'outils du SDK (`client.beta.messages.toolRunner` +
  `betaZodTool`), `tool_choice: auto` (le choix forcé d'un outil renvoie une
  erreur 400 sur Opus 5.5). Outils : `propose_script`, `estimate_cost`,
  `start_generation`, `get_status`, `list_characters`. Le blocage avant
  dépense se fait dans le code : `start_generation` refuse de partir sans
  confirmation explicite de l'utilisateur dans le fil.
- **Mise en cache** : la consigne système et les définitions d'outils sont
  stables et passent en cache ; la fiche des personnages et `story_so_far`
  viennent après.
- **Refus** : vérifier `stop_reason` avant de lire la réponse ; activer le
  repli côté serveur (`fallbacks: "default"`, en-tête bêta
  `server-side-fallback-2026-07-01`).

## Schéma

Tables : 10. Accès : RLS Postgres (`user_id = auth.uid()` sur chaque table) ;
le worker écrit avec la clé `service_role`. Fichier complet :
[`schema.sql`](schema.sql), appliqué avec succès sur Postgres 16.

```
profiles            1 par utilisateur ; budget mensuel optionnel
universes           tes thèmes : style_prompt, modèles par défaut
characters          description, personnalité, voice_id, reference_keys[]
series              univers fixé (on delete restrict), story_so_far
series_characters   n-n, on delete restrict côté personnage
projects            une vidéo ; mode, statut, script jsonb, clé du fichier final
scenes              position unique par projet, dialogue, prompts, modèles, durée
scene_characters    n-n
generation_jobs     un appel fournisseur ; idempotency_key unique, coût en µ$
agent_messages      blocs bruts de l'API, renvoyés tels quels
```

Contraintes dures trouvées pendant la recon :

- un seul montage en cours par projet (index unique partiel sur `generation_jobs`) ;
- un numéro d'épisode unique par série ;
- un épisode a forcément une série, et inversement (`episode_needs_series`) ;
- un personnage créé depuis une photo exige le consentement (`photo_needs_consent`) ;
- l'univers d'une série et les personnages utilisés ne peuvent pas être supprimés
  en dessous d'elle (`on delete restrict`) ;
- les coûts sont en **micro-dollars** (`bigint`) : une image coûte une fraction
  de cent, donc des centimes entiers perdraient la précision.

## API

Actions serveur Next.js sauf mention contraire. « moi » = utilisateur connecté,
vérifié par la RLS.

### F01 Vidéo express

| méthode chemin | fait | qui | entrée | sortie | flux |
| --- | --- | --- | --- | --- | --- |
| action `createProject` | crée un projet en brouillon | moi | mode, universe_id, idea, aspect_ratio, character_ids | project | F01 F02 F05 |
| action `suggestIdea` | une idée courte selon l'univers | moi | universe_id, series_id? | texte | F01 F04 |
| action `estimateCost` | coût estimé avant lancement | moi | project_id | µ$ par étape | F01 F05 |
| action `startGeneration` | déclenche la tâche `video.generate` | moi | project_id | run_id | F01 F04 |
| GET `/api/runs/:id/token` | jeton public de suivi Trigger.dev | moi (propriétaire) | — | jeton | F01 F02 F04 |
| GET `/api/projects/:id/download` | URL signée R2 (15 min) | moi | — | redirection 302 | F01 |

### F02 Agent

| méthode chemin | fait | qui | entrée | sortie | flux |
| --- | --- | --- | --- | --- | --- |
| POST `/api/agent/:projectId` | un tour de chat en flux (SSE) ; boucle d'outils | moi | message | flux de texte et d'étapes | F02 |
| GET `/api/agent/:projectId` | historique | moi | — | messages | F02 |

### F03 Personnages

| méthode chemin | fait | qui | entrée | sortie | flux |
| --- | --- | --- | --- | --- | --- |
| action `createCharacter` | crée la fiche et lance `character.sheet` | moi | name, description, personality, universe_id, source | character | F03 |
| POST `/api/uploads/sign` | URL d'envoi R2 pour une photo (≤ 10 Mo, jpeg/png/webp) | moi | type, taille | url, key | F03 |
| action `regenerateSheet` | relance les images de référence | moi | character_id | job | F03 |
| action `deleteCharacter` | supprime si aucune série ne l'utilise | moi | character_id | ok ou erreur | F03 |

### F04 Séries

| méthode chemin | fait | qui | entrée | sortie | flux |
| --- | --- | --- | --- | --- | --- |
| action `createSeries` | univers, personnages, format | moi | title, universe_id, character_ids, aspect_ratio | series | F04 |
| action `suggestNextEpisodes` | 3 idées à partir de `story_so_far` | moi | series_id | idées | F04 |
| action `createEpisode` | projet lié, numéro suivant | moi | series_id, idea | project | F04 |

### F05 Studio

| méthode chemin | fait | qui | entrée | sortie | flux |
| --- | --- | --- | --- | --- | --- |
| action `updateScene` | modifie dialogue, prompts, modèle, durée | moi | scene_id, champs | scene | F05 |
| action `reorderScenes` | change l'ordre (contrainte différée) | moi | project_id, scene_ids[] | ok | F05 |
| action `regenerateScene` | relance image et/ou clip et/ou voix d'une scène | moi | scene_id, steps[] | run_id | F05 |
| action `assemble` | relance seulement le montage | moi | project_id | run_id | F05 |

### F06 Coûts

| méthode chemin | fait | qui | entrée | sortie | flux |
| --- | --- | --- | --- | --- | --- |
| GET `/api/costs?month=` | total par mois, par étape, par modèle | moi | mois | agrégats | F06 |

Webhooks entrants : aucun au départ. Les tâches interrogent les fournisseurs
vidéo à intervalle régulier (`wait.for` de Trigger.dev, sans coût de calcul
pendant l'attente). Webhooks sortants : aucun.

Tâches Trigger.dev :

| tâche | déclencheur | fait |
| --- | --- | --- |
| `video.generate` | `startGeneration` | script (Claude) → pour chaque scène en parallèle (limite 3) : image → clip → voix → musique → `video.assemble` |
| `scene.image` / `scene.clip` / `scene.voice` | sous-tâches | un appel fournisseur, un `generation_job`, clé d'idempotence `scene:étape:tentative` |
| `video.assemble` | fin des scènes ou `assemble` | ffmpeg : concat, mix, sous-titres ASS, upload R2 |
| `character.sheet` | `createCharacter` | 3 à 4 images de référence d'un même personnage |
| `series.summarize` | fin d'un épisode | met à jour `story_so_far` (Claude, effort `low`) |
| `cleanup.orphans` | tous les jours à 3h17 UTC | supprime de R2 les fichiers sans ligne en base depuis plus de 7 jours |

## Les points qui piquent

- **Cohérence des personnages** : le risque n°1. Toujours passer les images de
  référence du personnage au modèle image, et animer *depuis* l'image validée
  (image → vidéo), jamais texte → vidéo. Tester 2 ou 3 modèles au jalon 1 sur
  le même personnage avant d'écrire le reste.
- **Idempotence** : une tâche relancée ne doit pas repayer un clip. Chaque appel
  passe par `generation_jobs.idempotency_key` (unique) ; si la ligne existe en
  `succeeded`, on réutilise sa sortie.
- **Concurrence** : un double clic sur « Générer » → l'index
  `one_active_assemble` et le statut du projet (`draft` → `scripting` en une
  seule requête `update ... where status = 'draft'`) bloquent le second lancement.
- **Limites de débit** : les API vidéo acceptent peu de requêtes simultanées.
  File Trigger.dev avec une concurrence de 3 par fournisseur, nouvelles
  tentatives avec attente exponentielle sur les erreurs 429 et 5xx.
- **Coûts qui dérapent** : un clip haut de gamme coûte des dizaines de fois une
  image. `estimateCost` avant chaque lancement, budget mensuel dans `profiles`
  vérifié par `startGeneration`, et l'agent doit annoncer le coût avant d'agir.
- **Taille des fichiers** : envois directs vers R2 par URL signée (pas via
  Vercel, limité à 4,5 Mo par requête). Photos ≤ 10 Mo.
- **Durées des modèles** : chaque modèle vidéo a ses durées autorisées
  (ex. 4 à 8 s). La table des modèles en code borne `duration_s` ; le script
  demandé à Claude respecte ces bornes.
- **Sous-titres** : un fichier ASS construit à partir de l'horodatage
  ElevenLabs, 2 à 4 mots par ligne pour le format vertical.
- **RLS des tables enfants** : `user_id = auth.uid()` ne vérifie pas que la
  scène appartient à *ton* projet. Sans conséquence avec un seul utilisateur ;
  si tu ouvres à d'autres, ajoute des politiques qui joignent le parent.
- **Temps réel** : la progression vient de Trigger.dev Realtime (métadonnées de
  la tâche), pas de sondage de la base.
- **Fuseaux horaires** : seulement des horodatages, en `timestamptz`, en UTC ;
  aucun calcul de calendrier.
- **RGPD / photos de vraies personnes** : case de consentement obligatoire et
  suppression en cascade (base + R2) quand on supprime le personnage.
- **Droits sur les vidéos** : vérifier les conditions de chaque fournisseur
  (usage commercial, mentions) avant de publier.

## Ordre de construction

1. **Tranche verticale** (moche mais complète) : S03 connexion → S06 formulaire
   express (univers codé en dur, pas de personnages) → S07 suivi → S08 lecteur
   et téléchargement. Tables : `profiles`, `universes`, `projects`, `scenes`,
   `generation_jobs`. Routes : `createProject`, `startGeneration`,
   `/api/runs/:id/token`, `/api/projects/:id/download`. Tâches :
   `video.generate`, `scene.*`, `video.assemble`. Choisir ici les modèles image
   et vidéo par défaut à partir d'un test de coût et de qualité.
2. **Indispensables** (`must`) : bibliothèque de personnages S12/S13 et leur
   injection dans les prompts (`characters`, `scene_characters`,
   `character.sheet`), S04 tableau de bord, musique, sous-titres, reprise de
   l'étape qui a échoué.
3. **Importants** (`should`) : création depuis une photo, univers modifiables,
   « suggérer une idée », séries S09/S10 (`series`, `series_characters`,
   `series.summarize`), Studio S11 (`updateScene`, `regenerateScene`), estimation
   des coûts et journal S15, S14 mes vidéos. Puis les optionnels (`could`) :
   agent S05, 16:9, voix multilingues, styles de sous-titres.
4. **Corrections issues de `/replica-entrepreneur`** : à ajouter quand il
   aura tourné.
