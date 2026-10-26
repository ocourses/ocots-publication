<!-- LTeX: language=fr-FR -->

# Journal des versions

Un cours **épingle une version** de ce dépôt (sous-module `publication/`).

```bash
git -C publication describe --tags --always
```

---

## Non publié

- Un dossier contenant des sous-modules git est publié avec leurs fichiers
  (jusqu'ici le gitlink seul était vu, d'où un dossier « vide » refusé). Un
  sous-module non initialisé est refusé avec un message explicite (#3).

---

## v1.1.0 — 2026-10-26

- `publier-etudiant --version` annonce la version ; une constante `VERSION` la
  porte, et un test vérifie qu'elle a sa section dans ce CHANGELOG.
- Workflow `release.yml` : un tag `vX.Y.Z` poussé crée la release GitHub, avec
  pour notes la section du CHANGELOG ; il échoue si la section manque ou si la
  version du script n'est pas celle du tag.

## v1.0.0 — 2026-10-25

Première version partagée, extraite de `scripts/publier-etudiant` de
`mesure-integration-enseignants` (PR #460).

- Entrées `[[fichier]]` et `[[dossier]]` (récursif, `exclure`).
- Qualificatif `miroir = true` : la cible d'un dossier devient identique à sa
  source, les suppressions sont listées dans le rapport et la PR.
- Garde-fous : cibles vides, absolues, hors du dépôt ou dans `.git` refusées,
  source vide refusée, miroir limité à sa cible et aux dossiers sélectionnés en
  entier.
- Le dépôt enseignant est celui du répertoire courant (ou `--config`), plus
  celui qui contient le script.
