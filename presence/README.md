# `presence/` — controle d'acces du personnel (visage + geste du pouce)

> Ce module est **hors du perimetre du sujet SENTINEL-X** : il vient d'une directive
> anterieure (pointage du personnel). Il reste utile au projet comme source de la liste
> blanche de la vision, mais il ne fait pas partie du rendu du workshop.

Module `presence/` : borne de pointage autonome (`scripts/run.py`), aussi utilisee par la plateforme web.

Un agent (technicien, garde) se place devant la webcam a l'entree du site. L'IA **reconnait son visage**, puis **lit le geste de sa main** :

| Geste | Action enregistree |
|---|---|
| 👍 Pouce en haut | **Arrivee** (heure d'arrivee) |
| 👉 Pouce sur le cote | **Pause** : 1er geste = depart en pause, 2e geste = retour |
| 👎 Pouce en bas | **Fin** (depart ; une pause en cours est fermee automatiquement) |

## Fonctionnement

```
webcam ──► YuNet (detection visage) ──► SFace (empreinte 128D) ──► comparaison base agents ──► nom
       └─► MediaPipe Hand Landmarker (21 points de la main) ──► regles geometriques ──► geste
                                     nom + geste tenus ~8 images ──► registre SQLite
```

- **Visage** : modeles OpenCV pre-entraines (`presence/faces.py`). Chaque agent est enregistre a partir
  de quelques photos. L'empreinte moyenne est comparee par similarite cosinus (seuil 0,363).
- **Geste** (`presence/gestures.py`) : le pouce compte seulement si les 4 autres doigts sont replies et le
  pouce tendu. Sa direction (base → bout) donne l'angle : haut (±35°), bas (±35°), cote (±35°).
  Une diagonale ne declenche rien.
- **Anti faux positifs** (`presence/stabilizer.py`) : le geste doit etre tenu 8 images de suite, puis
  5 s de delai avant un nouveau geste du meme agent. Un visage inconnu ne declenche rien.
- **Regles** (`presence/attendance.py`) : pas de pause avant l'arrivee, pas de double arrivee,
  rien apres la fin. Une nouvelle journee repart de zero.

## Installation

```bash
cd presence_ia
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_models.py
```

## Utilisation

```bash
# 1. Enregistrer chaque agent (ESPACE pour capturer 5 photos)
python scripts/enroll.py "Alice Martin"
python scripts/enroll.py "Bob Durand" --images photos/bob/    # ou depuis un dossier de photos

# 2. Lancer la borne (Q pour quitter)
python scripts/run.py

# 3. Feuille de presence du jour (+ export CSV)
python scripts/report.py --csv data/presence.csv
```

Exemple de rapport :

```
Agent               Arrivee   Fin       Pauses  Min pause  Min presence  Statut
Alice Martin        08:30     17:00     1       6.0        504.0         parti
```

Donnees produites (dans `data/`, ignore par git) : `faces.npz` (empreintes), `presence.db` (evenements).

## Tests

```bash
pytest -q
```

Les tests couvrent la classification des gestes (rotations, main ouverte, pouce replie),
le stabilisateur, les regles de presence et la base d'empreintes.

## RGPD : a lire avant un usage reel

La reconnaissance faciale traite des **donnees biometriques**, categorie sensible (art. 9 RGPD).
Pour le controle d'acces a un site sensible (centrale energetique), la CNIL l'admet sous
conditions strictes. Pour un deploiement reel il faudrait au minimum : information et
consentement du personnel, **alternative sans biometrie** (badge), analyse d'impact (AIPD),
traitement 100 % local (c'est le cas ici : aucune image n'est envoyee ni stockee, seulement les
empreintes), duree de conservation limitee et suppression a la demande
(`python scripts/enroll.py "Nom" --remove`).

Pour la demo du workshop, utiliser uniquement des membres de l'equipe volontaires.
