# Carte de recon : TrendStory (trendstory.io, web)

Périmètre : la boucle principale. Une idée devient une vidéo verticale finie
(script, images, animation, voix, sous-titres, musique), avec une bibliothèque
de personnages cohérents et des séries d'épisodes.
Pour : usage perso / interne. Le clone produit tes propres vidéos ; pas de
facturation client, mais un suivi de ce que coûte chaque génération.
Date : 2026-11-12

> Source unique : les pages publiques. Aucun compte n'a été utilisé, donc tous
> les écrans derrière la connexion (S04 à S15) sont **déduits** du site
> marketing, des guides et de la page tarifs. Si tu as ton propre compte
> TrendStory, des captures de ces écrans dans `replica/screens/` feraient
> passer la confiance de « moyenne » à « haute ».

## Sources

| # | source | URL | notes |
| --- | --- | --- | --- |
| 1 | site marketing | https://www.trendstory.io/en | les 4 modes, 7 thèmes, FAQ, 8 langues, formats 9:16 / 16:9 |
| 2 | page tarifs | https://www.trendstory.io/en/pricing | 3 plans, crédits, 17 modèles avec leur coût par seconde ou par image, recharges |
| 3 | guide : générateur vidéo IA | https://www.trendstory.io/en/make/ai-video-generator | le pipeline complet, choix du modèle par scène, sous-titres animés |
| 4 | guide : séries | https://www.trendstory.io/en/make/ai-video-series-generator | personnages récurrents, suggestions d'épisodes qui suivent l'intrigue, univers fixé au départ |
| 5 | guide : histoire en vidéo | https://www.trendstory.io/en/make/ai-story-video-generator | découpage en scènes, dialogues, passage en Studio |
| 6 | CGV | https://www.trendstory.io/en/cgv | crédits du plan non reportés, recharges sans expiration, paiement par Whop |
| 7 | connexion | https://www.trendstory.io/login | Google + email/mot de passe, mot de passe oublié, anti-robot |
| 8 | index des guides | https://www.trendstory.io/en/make | autres guides (TikTok, faceless, anime, modèles) |

Ce que disent les CGV (source 6) : rien contre le reverse engineering ni contre
un produit concurrent. Interdits : revendre ou redistribuer la plateforme,
contourner sa sécurité. Les vidéos générées *chez eux* sont leur propriété
intellectuelle, sous licence pendant l'abonnement. Dans ton clone, les vidéos
seront à toi (sous réserve des conditions des modèles que tu appelles).

## Boucle principale

Tu tapes une idée en une phrase et tu choisis un univers visuel. En environ
5 minutes, tu récupères une vidéo verticale complète, avec des personnages
qui gardent le même visage d'une vidéo à l'autre.

## Écrans

| ID | écran | route / accès | rôle | composants clés | états |
| --- | --- | --- | --- | --- | --- |
| S01 | Accueil marketing | `/en` | présenter les 4 modes et les thèmes | hero, cartes des modes, grille des thèmes, témoignages, FAQ, bandeau cookies | public |
| S02 | Tarifs | `/en/pricing` | plans et coût des modèles | bascule mensuel/annuel, cartes de plans, sélecteur de palier, tableau des modèles | public |
| S03 | Connexion / inscription | `/login`, `?mode=signup` | créer un compte, se connecter | bouton Google, email + mot de passe, lien mot de passe oublié, captcha | vide, erreur, captcha échoué |
| S04 | Tableau de bord *(déduit)* | après connexion | choisir un mode, voir ses projets récents | 4 cartes de mode, liste des projets, solde de crédits | vide (premier lancement), rempli |
| S05 | Agent IA *(déduit)* | mode « AI Agent » | discuter : l'agent pose des questions puis lance la création | fil de chat, saisie, cartes d'étapes en ligne, aperçu vidéo | vide, en cours, terminé, erreur, crédits insuffisants |
| S06 | Vidéo express : formulaire *(déduit)* | mode « Express » | thème + idée → vidéo | grille de thèmes, champ idée, bouton « suggérer une idée », choix des personnages, format, langue | vide, rempli, crédits insuffisants |
| S07 | Génération en cours *(déduit)* | après lancement | suivre le pipeline en direct | étapes (script, images, animation, voix, sous-titres, musique), vignettes de scènes | en cours, échec d'une étape, terminé |
| S08 | Résultat vidéo *(déduit)* | fin de génération | regarder, télécharger, passer en Studio | lecteur vidéo, Télécharger, Modifier dans Studio, Régénérer | prêt, erreur |
| S09 | Séries : liste *(déduit)* | mode « Séries » | voir ses séries | cartes de série (univers, personnages, nombre d'épisodes) | vide, rempli, verrouillé (plan Starter) |
| S10 | Série : détail + nouvel épisode *(déduit)* | ouvrir une série | enchaîner les épisodes | liste des épisodes, idées d'épisode suivant suggérées, champ idée | aucun épisode, épisodes, génération en cours |
| S11 | Studio *(déduit)* | mode « Studio » ou depuis S08 / S10 | régler chaque scène | liste des scènes, et pour chacune : image, dialogue, mouvement, modèle, durée ; coût estimé ; aperçu | brouillon, scène en génération, scène en erreur, rendu final |
| S12 | Bibliothèque de personnages *(déduit)* | menu | gérer ses personnages réutilisables | grille de fiches, préréglages, filtres par univers | vide, rempli, limite du plan atteinte |
| S13 | Créer un personnage *(déduit)* | depuis S12 ou un formulaire | décrire, téléverser une photo ou partir d'un préréglage | onglets description / photo / préréglage, aperçu, nom, personnalité | vide, génération, prêt |
| S14 | Mes vidéos / projets *(déduit)* | menu | retrouver ses vidéos et brouillons | grille, filtres par mode, statut | vide, rempli |
| S15 | Compte et crédits *(déduit)* | menu | plan, solde, recharges, langue | solde, historique de consommation, bouton recharger, langue de l'interface | — |

## Flux

```
F01 Créer une vidéo express
    S04 -> S06 (thème, idée) -> S07 -> S08 -> télécharger
    clics sur le chemin heureux : ~5 (mode, thème, saisie, Générer, Télécharger)
    durée annoncée : ~5 min
    cas limites : idée vide (« suggérer une idée »), crédits insuffisants avant
    lancement, une étape échoue (modèle en panne), langue de la voix différente
    de celle de l'interface

F02 Créer une vidéo en discutant avec l'agent
    S04 -> S05 (chat, questions, validation) -> S07 (dans le chat) -> S08
    clics : ~3 + les messages
    cas limites : idée floue (l'agent relance), changement d'avis en cours de
    génération, coût total annoncé avant de lancer

F03 Créer un personnage réutilisable
    S12 -> S13 (description | photo | préréglage) -> aperçu -> enregistrer
    clics : ~4
    cas limites : photo d'une vraie personne (consentement), limite du plan,
    visage qui dérive entre les aperçus

F04 Lancer une série et enchaîner les épisodes
    S09 -> nouvelle série (univers + personnages) -> S10 -> idée ou suggestion
    -> S07 -> S08 ; puis S10 -> « épisode suivant » (tient compte des épisodes
    précédents) -> S07 -> S08
    clics : ~6 pour le premier épisode, ~3 pour les suivants
    cas limites : univers non modifiable après création, personnage supprimé
    de la bibliothèque, histoire trop longue (découpée en épisodes)

F05 Affiner scène par scène dans le Studio
    S08 ou S10 -> S11 -> modifier dialogue / image / mouvement / modèle /
    durée d'une scène -> régénérer cette scène seulement -> rendu final -> S08
    clics : variable
    cas limites : changer le modèle d'une seule scène, durée hors des bornes du
    modèle (ex. 4 à 8 s), dépassement de la durée max de la vidéo

F06 Suivre et recharger ses crédits
    S15 -> recharger
    pour un usage interne, ce flux devient « voir ce que coûte chaque vidéo
    en appels d'API »
```

## Composants

| composant | variantes | états | utilisé sur |
| --- | --- | --- | --- |
| Bouton | principal, secondaire, fantôme, danger | défaut, survol, focus, désactivé, chargement | partout |
| Carte de mode | Agent, Express, Séries, Studio | défaut, verrouillée (plan) | S01, S04 |
| Tuile de thème | 7 univers + « nouveau » | défaut, sélectionnée | S01, S06, S09 |
| Champ idée | une ligne, multiligne | vide, rempli, suggestion en cours | S06, S10 |
| Fil de chat | message utilisateur, message agent, carte d'étape, carte vidéo | en cours de frappe, erreur | S05 |
| Suivi de pipeline | barre d'étapes, vignette de scène | en attente, en cours, ok, échec | S05, S07 |
| Lecteur vidéo | 9:16, 16:9 | chargement, lecture, erreur | S08, S10, S14 |
| Fiche personnage | préréglage, perso créé | sélectionnée, désactivée | S06, S10, S12 |
| Éditeur de scène | ligne repliée, panneau ouvert | brouillon, génération, erreur | S11 |
| Sélecteur de modèle | vidéo, image | disponible, verrouillé, coût affiché | S11 |
| Compteur de crédits | en-tête, détaillé | normal, bas, épuisé | partout, S15 |
| Fenêtre modale | confirmation, coût, crédits insuffisants | ouverte, fermée | S06, S11 |
| Toast | succès, erreur | — | partout |
| Sélecteur de langue | interface, voix | — | S03, S06, S15 |

## Modèle de données déduit

```
User        id, email, auth_provider (google | email), locale, created_at
            evidence: S03, FAQ langues
            confidence: high

Character   id, user_id, name, universe, description, personality,
            reference_images[], source (prompt | photo | preset), created_at
            evidence: S12/S13, guides séries et personnages (« fiche par
            personnage : visage, style, personnalité »)
            confidence: medium

Series      id, user_id, title, universe (fixé à la création), aspect_ratio,
            language, story_summary (pour suggérer la suite)
            evidence: guide séries
            confidence: medium

SeriesCharacter  series_id, character_id
            confidence: medium

Project     id, user_id, mode (agent | express | series | studio),
            series_id?, episode_number?, idea, universe, aspect_ratio
            (9:16 | 16:9), language, status (draft | generating | ready |
            failed), final_video_url, duration_s, created_at
            evidence: FAQ formats, tarifs (durée max par plan), S08
            confidence: medium

Scene       id, project_id, position, dialogue, narration, image_prompt,
            motion_prompt, image_model, video_model, duration_s, image_url,
            clip_url, voice_url, status
            evidence: Studio (« image, dialogue, mouvement, modèle, durée »)
            confidence: medium

SceneCharacter  scene_id, character_id
            confidence: guess

GenerationJob  id, scene_id | project_id, step (script | image | video |
            voice | subtitles | music | assemble), provider, model,
            credits_cost, status, error, started_at, finished_at
            evidence: suivi en direct, coût par seconde par modèle
            confidence: guess

AgentMessage  id, project_id, role, content, tool_calls (json)
            evidence: mode Agent « dans le chat »
            confidence: guess

CreditLedger  id, user_id, amount, kind (plan | topup | spend), job_id?
            evidence: tarifs, CGV
            confidence: high (chez eux) — pour toi, c'est un journal de coûts
```

Relations : User 1-n Character, User 1-n Series, User 1-n Project,
Series n-n Character, Series 1-n Project (épisodes), Project 1-n Scene,
Scene n-n Character, Scene 1-n GenerationJob, Project 1-n AgentMessage.

## Matrice des fonctionnalités

Voir `features.csv`. Must : 14, should : 11, could : 6, skip : 7.

## Hors périmètre (ne peut pas ou ne doit pas être cloné)

- **Leur modèle vidéo maison « TrendStory »** : propriétaire. Le clone appelle
  directement les modèles tiers via leurs API officielles (Veo, Seedance,
  Grok Imagine, Nano Banana, etc.), avec tes propres clés.
- **Boost (achat d'abonnés)** : enfreint les conditions de TikTok et
  d'Instagram. Exclu.
- **Les 750K créateurs, les comptes vitrines et les témoignages** : c'est leur
  communauté, pas une fonctionnalité.
- **Leurs personnages préréglés, thèmes visuels et exemples** : leur contenu.
  Tu crées tes propres préréglages.
- **Leur bibliothèque musicale** : à remplacer par de la musique libre de
  droits ou générée, avec une licence vérifiée.
- **Facturation Whop, plans et paliers** : inutiles pour un usage interne.
- **Les 8 langues d'interface** : commence par le français ; les voix
  multilingues restent faciles à garder.

## Taille

Écrans 15 (3 publics, 12 dans l'app), flux 6, entités 10.

Parties difficiles :
1. **Cohérence des personnages** : garder le même visage sur toutes les scènes
   et tous les épisodes (images de référence passées aux modèles image →
   vidéo). C'est la promesse centrale du produit.
2. **L'orchestration du pipeline** : script → découpage → images → clips →
   voix → sous-titres synchronisés → musique → montage ffmpeg. Ce sont des
   jobs longs et asynchrones, sur plusieurs fournisseurs, avec reprise sur
   échec scène par scène.
3. **L'agent conversationnel** : un LLM qui pose des questions puis appelle
   le pipeline comme outil, en annonçant le coût avant de lancer.

Autres points durs : la mémoire de l'intrigue pour suggérer l'épisode suivant,
les sous-titres animés, et la maîtrise des coûts d'API (un clip Seedance 2 de
5 s vaut des dizaines de fois une image).

Taille : **M** (quelques semaines) pour Express + personnages + séries.
Le Studio et l'Agent font passer à **L**.
