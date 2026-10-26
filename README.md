<!-- LTeX: language=fr-FR -->

# `ocots-publication` — publier les supports d'un cours vers son dépôt étudiant

Un cours a deux dépôts : le dépôt **enseignant** (sources LaTeX, corrigés,
sites en chantier), privé, et le dépôt **étudiant**, public, qui ne contient que
les supports à distribuer. Ce dépôt fournit `publier-etudiant`, qui copie ce
qu'il faut de l'un vers l'autre **par pull request**, selon un fichier
`publication.toml` propre à chaque cours. Python 3.11+ (bibliothèque standard
seulement), `git` et `gh` authentifié.

## Dans un cours

Comme `ocots-latex-template` et `ocots-conventions`, en sous-module épinglé :

```bash
git submodule add https://github.com/ocourses/ocots-publication publication
git -C publication checkout v1.0.0
```

Puis un lanceur `scripts/publier-etudiant`, qui garde les commandes habituelles :

```bash
#!/bin/sh
exec python3 "$(dirname "$0")/../publication/bin/publier-etudiant" "$@"
```

Le script s'exécute depuis le dépôt enseignant (celui du répertoire courant) et
lit son `publication.toml`, à la racine, ou `--config`.

## `publication.toml`

```toml
[depot]
chemin = "../mesure-integration"   # clone local du dépôt étudiant
branche = "main"                   # base des PR de publication

[[fichier]]
source = "poly/main.pdf"
cible = "cours/mesure-integration.pdf"

[[dossier]]
source = "site"
cible = "site"
miroir = true                      # défaut : false
exclure = ["node_modules", "package-lock.json", ".DS_Store"]
```

Les `source` sont relatifs au dépôt enseignant, les `cible` au dépôt étudiant.

Un **dossier** est copié récursivement : fichiers suivis par git ou non
ignorés, moins ceux de `exclure` (motifs fnmatch sur un nom, un chemin relatif
ou un dossier entier, côté source et côté cible).

Les sous-modules git présents dans un dossier sont parcourus récursivement :
leurs fichiers sont copiés dans le dépôt étudiant, et non leur seul gitlink.
Le sous-module doit donc être initialisé dans le dépôt enseignant. Par exemple,
avec un socle dans `site/socle/` :

```toml
[[dossier]]
source = "site"
cible = "site"
miroir = true
```

publie aussi `site/socle/...` dans le dépôt étudiant ; celui-ci n'a pas besoin
de cloner le sous-module.

Avec **`miroir = true`**, le contenu de la cible devient exactement celui de la
source : ce que la source n'a plus est supprimé de la cible, et listé sous
« Supprimés ». Sans miroir, **rien n'est jamais supprimé**. Garde-fous :

- le miroir ne touche que sa cible ;
- il n'agit que si le dossier est sélectionné **en entier** (`preparer site` ou
  `'site/*'` oui, `'site/js/*'` non) ;
- les fichiers d'autres entrées et ceux de `exclure` ne sont jamais supprimés ;
- une cible vide, `.`, absolue, hors du dépôt ou dans `.git` est refusée, comme
  une source vide.

## Utilisation

```bash
scripts/publier-etudiant simuler [motifs]    # rapport seul, rien n'est écrit
scripts/publier-etudiant preparer [motifs]   # worktree + branche publication/<date>, copie, commit local
scripts/publier-etudiant deployer            # pousse la branche et ouvre la PR (description = rapport)
scripts/publier-etudiant finaliser           # après fusion : nettoie worktree et branches
scripts/publier-etudiant etat                # publication en cours
scripts/publier-etudiant vider [motifs]      # prépare la suppression de tout (ou des motifs)
scripts/publier-etudiant initialiser         # dépôt étudiant vide : commit vide sur la branche de base
```

Le script travaille dans un worktree dédié et ne touche jamais au checkout du
dépôt étudiant. `simuler` et `etat` sont sans effet ; `preparer` et `vider`
n'écrivent qu'en local ; `deployer`, `finaliser` et `initialiser` agissent sur
GitHub. `scripts/publier-etudiant --help` détaille chaque commande.

## Tests

```bash
python3 -m unittest discover -s tests
```

## Publier une version

Versions sémantiques : majeure si `publication.toml` ou le comportement d'une
commande change de façon incompatible, mineure pour une fonction ajoutée,
corrective sinon. Procédure, comme pour `ocots-conventions` :

1. PR `chore(release): vX.Y.Z` : section `## vX.Y.Z — date` du CHANGELOG et
   constante `VERSION` de `bin/publier-etudiant` ;
2. une fois la PR fusionnée, tag annoté sur le commit de merge :
   `git tag -a vX.Y.Z -m vX.Y.Z && git push origin vX.Y.Z` ;
3. le workflow `release.yml` crée la release GitHub (notes = section du
   CHANGELOG) et vérifie que le script annonce bien le tag ;
4. les cours montent l'épingle de `publication/`, une PR par cours.
