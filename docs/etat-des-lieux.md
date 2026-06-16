# État des lieux — Projet 2 DevSecOps

## Ce qui fonctionne

| Élément | Statut | Détail |
|---|---|---|
| Pipeline CI/CD | ✅ | 8 étapes configurées dans `cloudbuild.yaml` |
| Tests unitaires | ✅ | 10 tests pytest passent (6 nominaux + 4 SQLi) |
| Gitleaks | ✅ | Bloquant, règle custom dans `.gitleaks.toml` |
| Semgrep (SAST) | ✅ | Bloquant sur injections SQL et failles applicatives |
| Trivy | ✅ | Bloquant sur CVE CRITICAL, `python-jose==3.4.0` sain |
| Checkov | ⚠️ | Configuré en `--soft-fail` — ne bloque jamais |
| Authentification API | ✅ | OIDC obligatoire (`--no-allow-unauthenticated`) |
| Rate limiting | ✅ | slowapi configuré sur tous les endpoints |
| Validation Pydantic | ✅ | Titre, contenu, recherche validés |
| Logs structurés | ✅ | JSON + trace-id sur chaque requête |
| 3 alertes Monitoring | ✅ | IAM, auth suspecte, pipeline échoué |
| Réseau VPC | ✅ | Subnet privé `10.0.0.0/24`, peering GCP |
| Cloud SQL | ✅ | Provisionné par Terraform, backups PITR activés |
| Secret Manager | ✅ | Mot de passe DB stocké, jamais dans le code |
| KMS | ✅ | Keyring + clé, rotation 90 jours |
| Conteneurs non-root | ✅ | `USER appuser` dans les deux Dockerfiles |
| Terraform staging | ✅ | Modules network, kms, secrets, database |
| Terraform prod | ✅ | Même structure, projet GCP séparé |
| State Terraform | ✅ | Versionné dans GCS |
| Documentation | ✅ | README, runbook, threat model, rapport |

---

## Ce qui ne fonctionne pas

| Élément | Statut | Problème |
|---|---|---|
| Connexion API → Cloud SQL | ❌ | L'API stocke les notes en mémoire (`notes_db = {}`), Cloud SQL n'est jamais utilisé |
| Worker archivage | ❌ | `archive_old_notes()` ne fait que logger, aucune logique réelle |
| KMS → Cloud SQL | ❌ | La clé KMS est créée mais jamais liée à Cloud SQL (CMEK non effectif) |
| Checkov bloquant | ❌ | `--soft-fail` dans `cloudbuild.yaml` — violations IaC ignorées |
| `deletion_protection` | ❌ | `false` sur Cloud SQL — suppression accidentelle possible en prod |
| Grafana | ❌ | Aucune configuration présente dans le projet |

---

## Problème critique à corriger avant la démo

| Priorité | Fichier | Problème |
|---|---|---|
| CRITIQUE | `README.md:6` | `password = '1234567'` en clair — Gitleaks devrait bloquer ce commit |

---

## Résumé

```
Infrastructure GCP    ✅ complète et sécurisée
Pipeline CI/CD        ✅ fonctionnel (sauf Checkov soft-fail)
Sécurité applicative  ✅ auth, rate limit, validation, logs
Code applicatif       ❌ API non connectée à Cloud SQL
Worker                ❌ logique d'archivage non implémentée
Grafana               ❌ absent du projet
```