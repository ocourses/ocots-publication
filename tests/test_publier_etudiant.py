"""Tests de scripts/publier-etudiant : dossiers, miroir, exclusions, garde-fous.

Lancer : python3 -m unittest discover -s tests
Chaque test monte un dépôt enseignant, un dépôt étudiant et son origine, dans
un répertoire temporaire ; rien ne touche GitHub (pas de deployer).
"""

import argparse
import contextlib
import importlib.machinery
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "publier-etudiant"
chargeur = importlib.machinery.SourceFileLoader("publier_etudiant", str(SCRIPT))
spec = importlib.util.spec_from_loader("publier_etudiant", chargeur)
pe = importlib.util.module_from_spec(spec)
sys.modules["publier_etudiant"] = pe
chargeur.exec_module(pe)


def git(depot, *args):
    subprocess.run(["git", "-C", str(depot), "-c", "user.name=t", "-c", "user.email=t@t",
                    *args], check=True, capture_output=True)


def ecrire(base, chemins):
    for chemin, contenu in chemins.items():
        f = Path(base) / chemin
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(contenu)


class Base(unittest.TestCase):
    def setUp(self):
        identite = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        for cle, valeur in identite.items():   # le script commite lui-même
            patcher = unittest.mock.patch.dict(os.environ, {cle: valeur})
            patcher.start()
            self.addCleanup(patcher.stop)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.ens, self.etu, origine = tmp / "ens", tmp / "etu", tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origine)], check=True)
        subprocess.run(["git", "clone", "-q", str(origine), str(self.etu)],
                       check=True, capture_output=True)
        ecrire(self.etu, {"README.md": "accueil\n"})
        git(self.etu, "add", "-A")
        git(self.etu, "commit", "-q", "-m", "init")
        git(self.etu, "push", "-q", "origin", "HEAD:main")
        self.ens.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.ens)], check=True)
        ecrire(self.ens, {"site/index.html": "v1\n", "site/js/a.js": "a\n",
                          "site/js/b.js": "b\n", "site/.gitignore": "node_modules/\n"})

    def valider(self):
        git(self.ens, "add", "-A")
        git(self.ens, "commit", "-q", "-m", "ens")

    def config(self, dossier: str, fichiers: str = ""):
        toml = self.ens / "publication.toml"
        toml.write_text(f'[depot]\nchemin = "{self.etu}"\n{fichiers}\n{dossier}\n')
        git(self.ens, "add", "-A")
        git(self.ens, "commit", "-q", "--allow-empty", "-m", "cfg")
        return pe.lire_config(toml, None)

    def rapport(self, cfg, motifs=()):
        base = pe.base_distante(cfg)
        self.n_arbres = getattr(self, "n_arbres", 0) + 1
        arbre = Path(self._tmp.name) / f"arbre{self.n_arbres}"
        git(cfg.depot, "worktree", "add", "-q", "--detach", str(arbre), base)
        self.addCleanup(git, cfg.depot, "worktree", "remove", "--force", str(arbre))
        choisies = pe.selectionner(cfg.entrees, list(motifs))
        return pe.comparer(cfg, choisies, arbre, pe.fichiers_presents(cfg.depot, base))

    def preparer(self, cfg, motifs=()):
        args = argparse.Namespace(motifs=list(motifs), depuis_zero=False)
        with contextlib.redirect_stdout(io.StringIO()):
            pe.cmd_preparer(cfg, args)
        return cfg.worktree

    def fusionner(self, cfg):
        """Prépare la publication, la pousse sur main et nettoie (comme PR + finaliser)."""
        wt = self.preparer(cfg)
        branche = pe.branche_en_cours(cfg)
        git(wt, "push", "-q", "origin", "HEAD:main")
        git(cfg.depot, "worktree", "remove", "--force", str(wt))
        git(cfg.depot, "branch", "-q", "-D", branche)

    def publier_puis_modifier_source(self, dossier, retouche):
        """Publie, fusionne en local, puis applique `retouche` à la source."""
        cfg = self.config(dossier)
        self.fusionner(cfg)
        retouche()
        self.valider()
        return self.config(dossier)


DOSSIER = '[[dossier]]\nsource = "site"\ncible = "site"\nmiroir = true\n'


class Dossiers(Base):
    def test_ajout_recursif(self):
        r = self.rapport(self.config(DOSSIER))
        self.assertEqual(len(r.ajoutes), 4)
        self.assertFalse(r.supprimes)

    def test_copie_dans_le_worktree(self):
        wt = self.preparer(self.config(DOSSIER))
        self.assertEqual((wt / "site/js/a.js").read_text(), "a\n")
        self.assertEqual((wt / "README.md").read_text(), "accueil\n")

    def test_modification(self):
        def retouche():
            (self.ens / "site/index.html").write_text("v2\n")
        r = self.rapport(self.publier_puis_modifier_source(DOSSIER, retouche))
        self.assertEqual(len(r.modifies), 1)
        self.assertEqual(len(r.inchanges), 3)

    def test_miroir_supprime_ce_qui_a_disparu(self):
        def retouche():
            git(self.ens, "rm", "-q", "site/js/b.js")
        r = self.rapport(self.publier_puis_modifier_source(DOSSIER, retouche))
        self.assertEqual(r.supprimes, ["site/js/b.js"])

    def test_miroir_supprime_dans_le_commit(self):
        def retouche():
            git(self.ens, "rm", "-q", "site/js/b.js")
        wt = self.preparer(self.publier_puis_modifier_source(DOSSIER, retouche))
        self.assertFalse((wt / "site/js/b.js").exists())
        self.assertTrue((wt / "site/js/a.js").exists())

    def test_sans_miroir_rien_n_est_supprime(self):
        sans = DOSSIER.replace("miroir = true", "miroir = false")

        def retouche():
            git(self.ens, "rm", "-q", "site/js/b.js")
        r = self.rapport(self.publier_puis_modifier_source(sans, retouche))
        self.assertFalse(r.supprimes)
        self.assertIn("site/js/b.js", r.hors_config)

    def test_miroir_ne_touche_que_sa_cible(self):
        ecrire(self.etu, {"autre/x.txt": "x\n"})
        git(self.etu, "add", "-A")
        git(self.etu, "commit", "-q", "-m", "autre")
        git(self.etu, "push", "-q", "origin", "HEAD:main")
        r = self.rapport(self.config(DOSSIER))
        self.assertIn("autre/x.txt", r.hors_config)
        self.assertFalse(r.supprimes)

    def test_exclusion_source_et_cible(self):
        ecrire(self.ens, {"site/notes.log": "log\n", "site/js/vieux.log": "log\n"})
        self.valider()
        cfg = self.config(DOSSIER + 'exclure = ["*.log"]\n')
        self.assertEqual(len(self.rapport(cfg).ajoutes), 4)
        # un fichier exclu déjà présent côté étudiant n'est pas supprimé
        ecrire(self.etu, {"site/cache.log": "x\n"})
        git(self.etu, "add", "-A")
        git(self.etu, "commit", "-q", "-m", "log")
        git(self.etu, "push", "-q", "origin", "HEAD:main")
        r = self.rapport(cfg)
        self.assertFalse(r.supprimes)

    def test_fichiers_ignores_par_git_exclus(self):
        ecrire(self.ens, {"site/node_modules/m/i.js": "m\n"})
        r = self.rapport(self.config(DOSSIER))
        self.assertFalse([a for a in r.ajoutes if "node_modules" in a])

    def test_selection_partielle_ne_supprime_rien(self):
        def retouche():
            git(self.ens, "rm", "-q", "site/js/b.js")
        cfg = self.publier_puis_modifier_source(DOSSIER, retouche)
        self.assertFalse(self.rapport(cfg, ["site/js/*"]).supprimes)
        self.assertEqual(self.rapport(cfg, ["site"]).supprimes, ["site/js/b.js"])
        self.assertEqual(self.rapport(cfg, ["site/*"]).supprimes, ["site/js/b.js"])

    def test_fichier_declare_a_part_protege_du_miroir(self):
        ecrire(self.ens, {"extra.txt": "e\n"})
        self.valider()
        cfg = self.config(DOSSIER, '[[fichier]]\nsource = "extra.txt"\ncible = "site/extra.txt"\n')
        self.fusionner(cfg)
        r = self.rapport(cfg)
        self.assertFalse(r.supprimes)


class Refus(Base):
    def refuse(self, dossier, message):
        with self.assertRaisesRegex(pe.Erreur, message):
            self.config(dossier)

    def test_cible_racine(self):
        self.refuse('[[dossier]]\nsource = "site"\ncible = "."\nmiroir = true\n', "refusée")

    def test_cible_vide(self):
        self.refuse('[[dossier]]\nsource = "site"\ncible = ""\nmiroir = true\n', "refusée")

    def test_cible_hors_depot(self):
        self.refuse('[[dossier]]\nsource = "site"\ncible = "../x"\nmiroir = true\n', "refusée")

    def test_cible_absolue(self):
        self.refuse('[[dossier]]\nsource = "site"\ncible = "/tmp/x"\nmiroir = true\n', "refusée")

    def test_cible_git(self):
        self.refuse('[[dossier]]\nsource = "site"\ncible = ".git/hooks"\n', "refusée")

    def test_source_introuvable(self):
        self.refuse('[[dossier]]\nsource = "absent"\ncible = "site"\n', "introuvable")

    def test_source_vide_apres_exclusion(self):
        self.refuse(DOSSIER + 'exclure = ["*"]\n', "vide")

    def test_miroir_non_booleen(self):
        self.refuse('[[dossier]]\nsource = "site"\ncible = "site"\nmiroir = "oui"\n', "true ou false")

    def test_cibles_en_collision(self):
        self.refuse(DOSSIER + '[[dossier]]\nsource = "site/js"\ncible = "site/js"\n', "en double")


if __name__ == "__main__":
    unittest.main()
