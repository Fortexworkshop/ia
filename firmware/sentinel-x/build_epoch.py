# Injecte l'heure de compilation : sert d'horloge de secours pour valider le certificat TLS
# quand le reseau de la table n'a pas acces a Internet (pas de NTP).
import time

Import("env")  # noqa: F821 (fourni par PlatformIO)
env.Append(CPPDEFINES=[("BUILD_EPOCH", int(time.time()))])  # noqa: F821
