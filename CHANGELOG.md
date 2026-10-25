<!-- LTeX: language=fr-FR -->

# Journal des versions

Un cours **épingle une version** de ce dépôt (sous-module `publication/`).

```bash
git -C publication describe --tags --always
```

---

## Non publié

---

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
