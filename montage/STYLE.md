# Guide de style LSMX — base pour tous les montages

Ce fichier résume ce qu'on a appris des vidéos LSMX déjà publiées (analyse faite
en novembre 2026 sur 88 vidéos, dont 8 regardées en détail). Les vidéos elles-mêmes
ne sont pas conservées. **On met ce fichier à jour après chaque nouveau montage.**

> Règle : aucun accès à Instagram ni TikTok (voir `CLAUDE.md`). Les rushs arrivent
> par Google Drive ou par ce dépôt. Les stats de nouvelles vidéos sont recopiées ici
> à la main par l'équipe.

## Ce qui marche (par ordre de résultats)

| Format | Exemples | Vues | Pourquoi ça marche |
|---|---|---|---|
| **Sortie de grange / trouvaille**, sans parole | YZ 250 de 1991 dans le foin ; 500 CR abandonné dans une grange | 357k / 135k (25k et 15k likes) | Moto rare et « oubliée », curiosité immédiate, 15–20 s, musique tendance (phonk) |
| **Le son d'une moto** | 250 CR sound ; 85 YZ | 30k–50k | Court, émotion de passionné, partage facile |
| **Face caméra / vlog avec gros coup** | Stock KTM racheté ; 3 KX à 1000 € | 30k–65k | Chiffre fort dans la 1re phrase (prix, quantité) |
| **Stock qui s'agrandit / teasing site** | « Le stock s'agrandit… » | 26k–67k | Montre la quantité, effet « caverne d'Ali Baba » |

## Ce qui marche moins

- Vidéos longues (plus de 50 s) sans accroche : souvent ~1 000 vues.
- Vue subjective « on attaque », emballage de colis, quotidien sans enjeu.
- Images sombres ou en basse résolution (576×1024).
- Hashtags mal écrits (`#motocros`) ou trop génériques.

## Règles de montage (déjà dans `lsmx_montage.py`)

1. **Accroche dans les 2 premières secondes** : bandeau rouge LSMX, texte court (5 mots max),
   avec un chiffre si possible (« 2000 pièces », « 1000 € », « 1991 »).
2. **Format** : 1080×1920, couleurs plus vives, netteté, léger zoom continu.
3. **Rythme** : couper tous les silences et hésitations (voix off / face caméra).
4. **Sous-titres mot par mot** : blanc, mot prononcé en jaune, 2–3 mots à la fois. Validé par l'équipe.
5. **Effets** sur mots-clés (emoji + son), au moins 2,5 s d'écart (voir `effets.json`).
6. **Pas de barre de progression rouge** (refusée par l'équipe).
7. **Carte de fin** : LSMX + lsmx-pieces.com + « Abonne-toi pour la suite ».
8. Son normalisé à -14 LUFS, musique baissée automatiquement sous la voix.
9. **Effet pause** (validé) : image figée sur la fin du 1er plan quand on dit « pause »,
   icône ⏸, la souris arrive et clique (son de clic), ▶, puis la musique démarre.
   Option `--pause <seconde>`.

## Publication

- Titre : une phrase avec le chiffre fort, plus une question pour faire commenter.
- 5–6 hashtags : la marque (`#ktm`, `#honda`, `#cr250`…) + `#motocross` + `#piecesmoto`
  + `#enduro` + `#fyp` + `#pourtoi`.
- Ajouter le son tendance dans l'appli TikTok, volume 10–15 %.
- Couverture : la miniature (`miniature.py`) ou l'image avec le bandeau rouge.

## Historique des montages

| Date | Vidéo | Options | Retour de l'équipe | Stats (à remplir) |
|---|---|---|---|---|
| 2026-11 | Stock concessionnaire KTM (35 s) | `--voix --pause 3.37 --hook "On rachète un stock KTM" --sub "2000 références neuves"` + beat LSMX | « Vraiment pas mal » ; sous-titres OK ; barre rouge refusée | vues : … / likes : … |
| 2026-11 | Teaser Black Friday 100 % code (18 s) + version Jour J | `teaser/` (config.js) | à venir | vues : … / likes : … |

## Idées à tester

- Zooms « punch » sur les mots forts (prix, marque).
- Versions avec un vrai son tendance fourni en mp3.
- Miniature avec visage + réaction.
- Format « sortie de grange » systématique pour chaque moto rare rentrée.
