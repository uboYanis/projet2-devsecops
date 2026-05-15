# Threat Model — Projet 2 DevSecOps

## Acteurs

| Acteur | Type | Niveau de confiance |
|---|---|---|
| Développeur | Humain interne | Élevé |
| Pipeline Cloud Build | Machine | Élevé (limité aux droits SA) |
| `notes-api-sa` | Machine | Moyen (secretAccessor + cloudsql.client) |
| `notes-worker-sa` | Machine | Faible (logging uniquement) |
| Utilisateur API | Externe | Non confiance (doit s'authentifier OIDC) |
| Attaquant externe | Externe | Zéro confiance |

## Menaces identifiées (STRIDE)

| Catégorie | Menace | Vecteur | Contrôle en place | Statut |
|---|---|---|---|---|
| **Spoofing** | Usurpation d'identité API | Token volé / rejeu | OIDC TTL court, Cloud Run vérifie signature Google | ✅ Mitigé |
| **Tampering** | Modification image en transit | Image non signée | Trivy bloque CVE critiques au build | ✅ Mitigé |
| **Repudiation** | Action non tracée | Absence de logs | Cloud Logging + trace-id sur chaque requête | ✅ Mitigé |
| **Info Disclosure** | Fuite secret dans repo | Commit avec credential | Gitleaks dans CI (bloquant) + Secret Manager | ✅ Mitigé |
| **Info Disclosure** | Accès bucket public | Mauvaise config ACL | `publicAccessPrevention` enforced | ✅ Mitigé |
| **Info Disclosure** | Injection SQL | Input utilisateur non validé | Semgrep SAST (bloquant) + requêtes paramétrées | ✅ Mitigé |
| **DoS** | Épuisement quota Cloud Run | Flood requêtes | Rate limiting slowapi (10 req/min POST) | ✅ Mitigé |
| **Elevation of Privilege** | IAM trop large | SA avec rôle owner | Least privilege + audit IAM | ✅ Mitigé |
| **Supply chain** | Dépendance vulnérable | `pip install` | Trivy scan image (exit-code 1 sur CRITICAL) | ✅ Mitigé |
| **Exposure** | Service public sans auth | `allUsers` sur Cloud Run | `--no-allow-unauthenticated` + org policy | ✅ Mitigé |

## Attaques démontrées

| # | Attaque | Preuve avant | Preuve après |
|---|---|---|---|
| 1 | Supply chain (CVE-2024-33663 python-jose) | Build bloqué Trivy | Build vert après patch 3.4.0 |
| 2 | Fuite secret CI/CD | Build bloqué Gitleaks | Build vert après suppression |
| 3 | IAM trop permissif | `roles/owner` sur SA | Least privilege confirmé |
| 4 | Exposition publique | HTTP 200 sans token | HTTP 403 après révocation |
| 5 | Injection SQL | Build bloqué Semgrep (3 règles) | Build vert après requête paramétrée |
| 6 | Exfiltration stockage | HTTP 200 fichier public | HTTP 403 après publicAccessPrevention |

## Résidus de risque acceptés

| Risque | Justification |
|---|---|
| Pas de WAF dédié | Hors budget crédits académiques |
| PITR Cloud SQL limité à 7 jours | Suffisant pour le contexte académique |
| Pas de rotation automatique secrets | Rotation manuelle documentée dans le runbook |
