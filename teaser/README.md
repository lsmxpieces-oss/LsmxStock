# Teaser Black Friday LSMX — 100 % généré par code

Aucune image, aucun logo, aucune vidéo : pièces dessinées en vectoriel (Canvas), textes animés,
particules, effets et bande son générée en Python (numpy).

## Modifier
Tout est dans **`config.js`** : textes (2 versions : `teaser` et `jourj`), couleurs, remise, dates,
prix d'exemple (le prix barré est calculé automatiquement), heure de publication (pour le compte à rebours),
rythme (`timeline`, BPM).

## Rendre
```
node teaser/render.mjs teaser          # → teaser/out/teaser/
node teaser/render.mjs jourj           # → teaser/out/jourj/
node teaser/render.mjs teaser --apercu # 1 image par seconde, pour contrôle
```
Sorties : `lsmx-bf-<version>.mp4` (avec son), `lsmx-bf-<version>-muet.mp4`, `cover.png`.

Prérequis : Node + Playwright (Chromium), ffmpeg, Python 3 + numpy. Polices Anton / Inter (OFL) dans `fonts/`.

## Fichiers
- `config.js` — le seul fichier à modifier
- `parts.js` — 8 pièces dessinées (disque, couronne, pignon, piston+bielle, amortisseur, jante, silencieux, levier)
- `main.js` — scènes, animations, effets (flash, tremblement, décalage RGB, grain, particules)
- `son.py` — bande son (2-temps, 140 BPM, whoosh, impacts)
- `render.mjs` — capture image par image + ffmpeg
