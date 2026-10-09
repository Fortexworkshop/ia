## Ce que fait cette PR

<!-- En deux ou trois phrases : le problème, et ce que la PR change. -->

## Vérifications

- [ ] `python -m pytest -q` passe — et j'ai regardé les tests **ignorés** (`-rs`), pas seulement les
      tests passés
- [ ] Aucun secret dans le diff (`git ls-files | grep -Ei "\.env$|certs/|passwd$|mqtt-users\.env|faces\.npz|people\.db|presence_log|\.pem$|\.key$|\.crt$|sentinel_config\.h$"` doit être vide)
- [ ] J'ai relu mon propre diff ligne à ligne avant de demander une relecture
- [ ] La documentation concernée est à jour (`README.md`, `docs/`, `DECISIONS.md` si la décision est
      structurante)
- [ ] Si la PR touche le rendu : le deck ou le document a été **regénéré et regardé**

## Ce que le relecteur doit vérifier

1. La logique correspond-elle à la tâche décrite ?
2. Les cas d'erreur sont-ils traités ?
3. Un secret ou une régression de sécurité s'est-il glissé dans le diff ?

## Points d'attention

<!-- Ce qui est fragile, ce qui reste ouvert, ce qui a été écarté. -->
