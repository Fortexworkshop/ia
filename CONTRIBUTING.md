# Contribuer — FORTEX / SENTINEL-X

Règles de travail du dépôt. Elles reprennent les exigences du
[guide de méthodologie](docs/reference/GUIDE_Methodologie_Rigoureuse.md) et les adaptent à ce
projet : **ni linter ni CI n'est configuré**, la vérification est donc manuelle et explicite.

---

## 1. Branches et flux

| Branche | Rôle |
|---|---|
| `dev` | **branche de travail.** Tout part de là, tout y revient. |
| `main` | branche publiée. **Mise à jour uniquement par Pull Request**, jamais en direct. |
| `livrables` | branche d'archive des rendus présentés. |

Cycle normal :

```bash
git switch dev && git pull
git switch -c feat/mon-sujet        # ou fix/, docs/, chore/
# … commits …
git push -u origin feat/mon-sujet
gh pr create --base dev             # puis relecture, puis fusion
```

Une fois la PR fusionnée dans `dev`, `main` suit par une PR `dev` → `main`.

---

## 2. Commits

- **Conventional Commits**, en **français** : `feat(vision): …`, `fix(backend): …`, `docs: …`,
  `chore(depot): …`, `refactor(dashboard): …`.
- Le *scope* est le sous-système : `backend`, `dashboard`, `vision`, `anomaly`, `infra`, `security`,
  `depot`, `docs`, `livrables`.
- Un commit = une intention. Un `fix` qui embarque un renommage se relit mal.
- Pas de trailer `Co-authored-by` automatique : les commits portent leur auteur, et rien d'autre.

---

## 3. Pull requests

Le gabarit est dans [`.github/pull_request_template.md`](.github/pull_request_template.md). Il est
court, et sa checklist est à remplir vraiment :

- [ ] les tests passent (`python -m pytest -q`) ;
- [ ] **aucun secret** dans le diff (voir § 5) ;
- [ ] le diff a été relu par l'auteur avant de demander une relecture ;
- [ ] la documentation concernée est à jour.

**Une PR se relit par quelqu'un d'autre que l'auteur.** Une auto-validation, même rigoureuse, ne
remplace pas un second regard. Le relecteur vérifie trois choses au minimum :

1. la logique correspond-elle à la tâche décrite ;
2. les cas d'erreur sont-ils traités ;
3. un secret ou une régression de sécurité s'est-il glissé dans le diff.

Un désaccord se règle **dans la PR**, par la discussion. Jamais par une fusion forcée.

---

## 4. Interdits sur l'historique

- **Aucune réécriture d'historique** (`rebase -i`, `commit --amend` sur une branche partagée,
  changement de dates) sans prévenir et sans accord explicite de l'équipe.
- **Aucun `git push --force`** sur `dev`, `main` ou `livrables`.
- Si un `subtree push` refuse en avance rapide, **on regarde l'écart avant** — jamais de `--force`
  par défaut. Un `--force` sur un dépôt public réécrit l'histoire de tout le monde.

---

## 5. Ce qui ne doit jamais être commité

| Interdit | Pourquoi | Où c'est exclu |
|---|---|---|
| `.env`, `infra/.env` | secrets | `.gitignore`, `infra/.gitignore` |
| `infra/certs/`, `infra/mqtt-users.env`, `infra/mosquitto/config/passwd` | matériel cryptographique et comptes | `infra/.gitignore` |
| `firmware/sentinel-x/include/sentinel_config.h` | contient les identifiants Wi-Fi et MQTT | `firmware/sentinel-x/.gitignore` |
| `data/` (`faces.npz`, `people.db`, `presence_log.db`) | **données biométriques** | `.gitignore` |
| `docs/reference/*.pdf` | documents tiers, dépôt public | `.gitignore` |

Les fichiers `*.example` ne contiennent **que des valeurs factices**. `scripts/configure.py` génère
tout le reste localement, et il est **idempotent** : il n'écrase jamais une valeur existante.

En cas de doute, avant de committer :

```bash
git ls-files | grep -Ei "\.env$|certs/|passwd$|mqtt-users\.env|faces\.npz|people\.db|presence_log|\.pem$|\.key$|\.crt$|sentinel_config\.h$"   # doit être vide
```

---

## 6. Tests et vérification

```bash
python -m pytest -q                     # suite complète (114 tests)
python -m pytest tests/test_backend.py -q
```

Deux pièges :

- Plusieurs fichiers utilisent `pytest.importorskip` : un test « passé » peut en réalité avoir été
  **ignoré** faute de dépendance. Lancer `pytest -q -rs` et **regarder le nombre d'ignorés**.
- Le firmware (`firmware/sentinel-x`, PlatformIO) n'est pas couvert par `pytest`.

Contrôles qui demandent la pile lancée :

```bash
python scripts/check_security.py        # 7 contrôles : TLS, comptes MQTT, ACL, jeton
python scripts/bench_vision.py          # latence de la vision (exigence < 100 ms)
```

### Vérification indépendante

**Ne jamais accepter un rapport sur sa seule déclaration** — celui d'un coéquipier comme celui d'un
agent. Un commit donné comme poussé se vérifie sur le dépôt distant (`git ls-remote`), pas en local.
Une mesure de sécurité donnée comme « en place » se teste pour de vrai. Et **un silence sur un point
demandé n'est pas une confirmation** : tant que ce n'est pas confirmé, c'est non fait.

---

## 7. Sous-dépôts `dev` et `infra`

`dev/` et `infra/` sont des sous-arbres (`git subtree`) de dépôts publiés séparément. Pour
récupérer leurs évolutions, **depuis `Fortex/`** :

```bash
git subtree pull --prefix=dev   https://github.com/Fortexworkshop/dev.git   dev
git subtree pull --prefix=infra https://github.com/Fortexworkshop/infra.git main
```

Pour republier :

```bash
git subtree push --prefix=dev   https://github.com/Fortexworkshop/dev.git   dev
git subtree push --prefix=infra https://github.com/Fortexworkshop/infra.git main
```

`git subtree` n'est pas fourni avec `git` : si la commande est inconnue, installer le script
`git-subtree.sh` dans un dossier du `PATH` (`~/.local/bin/git-subtree`).

---

## 8. Chaîne de rendu

Depuis `Fortex/`, tout est régénérable :

```bash
python docs/dossier/build.py     --group 20 --out rendus   # dossier A4 + poster A3
python docs/dossier/bento.py     --group 20 --out rendus   # deck Bento
python docs/dossier/bento2pptx.py --group 20               # export PowerPoint
node   docs/dossier/bento_check.js rendus/SENTINEL-X-G20.bento.html /tmp/controle
```

`bento_check.js` interroge `window.bento.validate()` et capture chaque slide : **le deck se regarde
avant d'être livré** — un débordement de texte est invisible dans le JSON et évident à l'écran.

Les livrables sont dans `rendus/`, les intermédiaires sont ignorés par Git.

---

## 9. Écrire une décision

Toute décision technique structurante se consigne dans [`DECISIONS.md`](DECISIONS.md) **au moment
où elle est prise**, en trois lignes : quoi, pourquoi, options écartées. Pas de reconstitution de
mémoire des semaines plus tard — c'est précisément ce que ce journal sert à éviter.

---

## 10. Langue et style du code

- **Français** pour le README, la documentation, les commentaires et les messages de commit.
- Commentaire seulement quand il apporte quelque chose : le *pourquoi*, jamais le *comment*.
- Les identifiants, eux, restent en anglais (`ingest_reading`, `safety_alarm`) : le code se lit avec
  le vocabulaire de son domaine.
