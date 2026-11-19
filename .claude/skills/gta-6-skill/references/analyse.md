# Analyse de performance et boucle d'amélioration

## Données
Saisies par plateforme, séparément (`tracker.py update --platform tiktok|youtube`), depuis
TikTok Studio / YouTube Studio, un export, ou un connecteur. Champ inconnu = laissé vide.
Ne jamais estimer ni inventer un chiffre.

## Indicateurs calculés
- **Engagement** TikTok = (likes + commentaires + partages) / vues.
- **Engagement** YouTube = (likes + commentaires) / vues ; abonnés gagnés suivis à part.
- **Score plateforme** = log10(1 + vues) × (1 + 2 × engagement) [× bonus abonnés YouTube, max +10 %].
  Sert uniquement à comparer les plateformes pour un même clip. La rétention n'y entre pas
  (les valeurs TikTok et Shorts ne sont pas comparables) : elle est analysée à part.
- **Performance globale** (selon la meilleure plateforme en vues) : Viral ≥ 100k, Fort ≥ 20k,
  Moyen ≥ 3k, Faible < 3k.
- **Meilleure plateforme** : TikTok, YouTube Shorts, Équivalent (écart < 8 %), ou « seule publiée ».

## Lecture du rapport
1. Totaux par plateforme : quelle plateforme progresse, laquelle stagne.
2. Par clip : meilleure plateforme + diagnostic croisé (portage, écart de rétention, d'engagement).
3. Par streamer et par type de moment : quels moments marchent où.

## Recommandations à produire après chaque rapport
- 3 actions concrètes pour TikTok et 3 pour YouTube Shorts (séparées).
- Types de moments à privilégier / abandonner par plateforme.
- Durée efficace observée par plateforme (comparer rétention vs durée).
- Hooks et titres gagnants à réutiliser comme modèles.
- Clips à porter sur l'autre plateforme, clips à republier avec un nouvel emballage.
- Créneaux de publication à tester (hypothèses à valider, pas des certitudes).

## Boucle
Repérer → monter → publier sur les deux → mesurer à J+1, J+3, J+7 → rapport → ajuster la
sélection, les hooks et les packs des prochains clips.
