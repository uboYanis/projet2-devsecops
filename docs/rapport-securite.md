# Rapport de Sécurité — Projet 2
## DevSecOps avancé : CI/CD & IaC policy-gated

**Cours** : Sécurité du Cloud — James Ortiz  
**Groupe** : [Prénom NOM], [Prénom NOM], [Prénom NOM]  
**Date de rendu** : Mai 2026  
**Cloud** : Google Cloud Platform (GCP) — région `europe-west1`  
**Dépôt Git** : https://github.com/uboYanis/projet2-devsecops  

---

## Table des matières

1. [Questionnaire projet cloud](#1-questionnaire-projet-cloud)
2. [Architecture technique](#2-architecture-technique)
3. [Qualité du code](#3-qualité-du-code)
4. [DevOps & CI/CD](#4-devops--cicd)
5. [Contrôles de sécurité obligatoires](#5-contrôles-de-sécurité-obligatoires)
6. [Modèle de menaces](#6-modèle-de-menaces)
7. [Démonstration des attaques](#7-démonstration-des-attaques)
8. [Observabilité et alerting](#8-observabilité-et-alerting)
9. [Guide de démo](#9-guide-de-démo)
10. [Conclusion et résidus de risque](#10-conclusion-et-résidus-de-risque)

---

## 1. Questionnaire projet cloud

> Ce questionnaire a été rempli au début du projet et mis à jour à la fin.

### 1.1 Résumé du projet

**Description**  
API REST de gestion de notes déployée sur GCP, composée de deux microservices :
- `notes-api` : API CRUD (créer, lire, supprimer des notes) en FastAPI (Python 3.11)
- `notes-worker` : Worker d'archivage automatique des notes de plus de 30 jours

**Finalité**  
Démontrer une approche DevSecOps complète où chaque commit déclenche automatiquement une chaîne de contrôles de sécurité avant tout déploiement. Le pipeline bloque automatiquement en cas de non-conformité (CVE critique, secret en clair, IaC dangereuse, injection SQL).

**Solution technique envisagée**

| Composant | Technologie |
|---|---|
| Compute | Cloud Run (conteneurs serverless managés) |
| Base de données | Cloud SQL PostgreSQL 15 (IP privée) |
| CI/CD | Cloud Build connecté à GitHub |
| Registre images | Artifact Registry |
| Secrets | Secret Manager |
| Chiffrement | Cloud KMS (rotation 90 jours) |
| Logs | Cloud Logging (JSON structuré + trace-id) |
| Alerting | Cloud Monitoring (3 alertes) |
| IaC | Terraform 1.14 avec modules réutilisables |

---

### 1.2 Fiche d'identité du projet

**Maîtrise d'ouvrage / Sponsor**  
Cours Sécurité du Cloud — EPISEN / James Ortiz

**Couverture du projet**  
Locale (projet académique) — données hébergées en Europe (`europe-west1`, Belgique)

**Contraintes projet**

| Contrainte | Détail |
|---|---|
| Coûts | Crédits GCP $300 / 90 jours |
| Délai | 6 à 8 semaines |
| Données | Aucune donnée personnelle réelle |
| SLA | Académique (Cloud Run SLA 99,95% en référence) |

**Type de solution**  
Transactionnel — API REST synchrone avec worker asynchrone planifié

---




### 1.3 Acteurs du projet

**Chef de projet interne**  
[À compléter : Prénom NOM]

**Usagers du service**
- Clients API (curl, Postman, applications)
- Pipeline CI/CD (Cloud Build — automatique)
- Administrateurs GCP (accès console avec MFA)

**Correspondants par catégorie d'usagers**

| Catégorie | Correspondant |
|---|---------------|
| Développeurs | Assala]       |
| Opérations | [A]           |
| Sécurité | [À compléter] |

**Maîtrise d'œuvre externalisée**  
Aucune — projet réalisé intégralement par le groupe.

---

### 1.4 Historique du périmètre

**Application existante ou création ?**  
Création from scratch — aucune application ni base de code préexistante.

**Audits ou évaluations sécurité déjà réalisés ?**  
Aucun audit préalable. Ce projet constitue la première évaluation de sécurité du système. Les contrôles ont été conçus dès la phase de conception (Security by Design).

---

### 1.5 Hébergement

**Modèle cloud**  
Cloud public — Google Cloud Platform

**Type d'offre**  
PaaS : Cloud Run (compute serverless), Cloud SQL managé, services GCP managés

**Hébergeur / région / pays**  
Google Cloud — `europe-west1` — Belgique  
Données hébergées en Europe, soumises au RGPD.

**Réseau**

| Composant | Configuration |
|---|---|
| VPC | `staging-vpc` dédié, auto-création désactivée |
| Subnet | `staging-subnet` — `10.0.0.0/24` |
| Cloud SQL | IP privée uniquement (peering Service Networking) |
| Cloud Run | `--no-allow-unauthenticated` + org policy |
| Accès Internet | HTTPS uniquement sur Cloud Run (TLS) |

**Chiffrement transit / stockage**

| Type | Implémentation |
|---|---|
| Transit | TLS 1.2+ géré par Cloud Run (certificat `*.a.run.app`) |
| Stockage | Google-managed + CMEK via Cloud KMS |
| Clé KMS | `staging-notes-keyring/db-encryption-key` — rotation 90 jours |

**Archivage, rétention, sauvegardes**

| Paramètre | Valeur |
|---|---|
| Backups Cloud SQL | Automatiques quotidiens (02h00 UTC) |
| PITR | Activé (Point-In-Time Recovery) |
| Rétention | 7 jours |
| State Terraform | Bucket GCS versionné (`tf-state-notes-staging`) |
| RPO | 1 heure |
| RTO | 15 minutes |

---

### 1.6 Gouvernance / Contrat

**SLA attendus**  
Académique — Cloud Run offre 99,95% de disponibilité en production (référence).

**Réversibilité**  
Infrastructure entièrement démantelable via `terraform destroy`. Le state GCS versionné permet de rejouer le déploiement depuis zéro à tout moment.

**Effacement des données**  
```bash
gcloud sql instances delete staging-notes-db --project=projet2-staging
gcloud storage rm -r gs://notes-archives-projet2-staging
terraform destroy -var="project_id=projet2-staging"
```

**Engagements de communication sur incident**  
Alertes Cloud Monitoring configurées avec notification par email du groupe. Runbook documenté dans `docs/runbook.md`.

---

### 1.7 Sécurité des données et des accès

**Données sensibles / RGPD**  
Aucune donnée personnelle réelle traitée. Les notes sont des données fictives de démonstration. Pas de traitement RGPD applicable dans ce contexte académique.

**Filtrage des accès**

| Ressource | Contrôle d'accès |
|---|---|
| Cloud Run API | Authentification OIDC obligatoire (token Bearer Google) |
| Cloud SQL | Accessible uniquement depuis le VPC privé |
| Secret Manager | SA autorisés uniquement (`secretmanager.secretAccessor`) |
| Bucket GCS | `publicAccessPrevention` enforced |
| Console GCP | Comptes admin avec MFA |

**MFA / Authentification forte**  
Comptes GCP administrateurs protégés par MFA (Google Workspace). Service accounts authentifiés via tokens OIDC gérés par GCP (TTL ~1 heure, rotation automatique).

**API externes et mesures de sécurité**  
Aucune dépendance à des API externes en production. Toutes les communications restent internes au VPC GCP.

---

## 2. Architecture technique

### 2.1 Diagramme logique

```
┌──────────────────────────────────────────────────────────────────────┐
│                        GCP — projet2-staging                          │
│                                                                        │
│  Développeur                                                           │
│      │                                                                 │
│      │ git push                                                        │
│      ▼                                                                 │
│  GitHub ──webhook──► Cloud Build                                       │
│                           │                                           │
│              ┌────────────▼────────────┐                             │
│              │     Pipeline CI/CD       │                             │
│              │  1. pytest (6 tests)     │                             │
│              │  2. Gitleaks (secrets)   │                             │
│              │  3. Semgrep (SAST)       │                             │
│              │  4. Checkov (IaC)        │                             │
│              │  5. Build Docker         │                             │
│              │  6. Trivy (CVE image)    │                             │
│              │  7. Push image           │                             │
│              │  8. Deploy Cloud Run     │                             │
│              └────────────┬────────────┘                             │
│                           │                                           │
│              ┌────────────▼────────────┐                             │
│              │    Artifact Registry     │                             │
│              │  notes-repo/api:SHA      │                             │
│              └────────────┬────────────┘                             │
│                           │                                           │
│         ┌─────────────────▼──────────────────┐                      │
│         │          Cloud Run                   │                      │
│         │     notes-api-staging                │                      │
│         │  (--no-allow-unauthenticated)        │                      │
│         │  Rate limiting : 10 req/min POST     │                      │
│         │  Logs JSON + trace-id                │                      │
│         └─────────┬────────────────────────────┘                     │
│                   │                                                    │
│    ┌──────────────▼─────────────────────────────┐                   │
│    │              VPC Privé (10.0.0.0/24)        │                   │
│    │  ┌──────────────┐    ┌────────────────────┐ │                   │
│    │  │  Cloud SQL   │    │   Secret Manager   │ │                   │
│    │  │ PostgreSQL15 │    │  staging-db-pass   │ │                   │
│    │  │ (IP privée)  │    └────────────────────┘ │                   │
│    │  │ Backup PITR  │    ┌────────────────────┐ │                   │
│    │  └──────────────┘    │    Cloud KMS       │ │                   │
│    │                      │ rotation 90 jours  │ │                   │
│    │                      └────────────────────┘ │                   │
│    └─────────────────────────────────────────────┘                   │
│                                                                        │
│    Cloud Logging ◄── tous les services (JSON + trace-id)             │
│    Cloud Monitoring ── 3 alertes (IAM, auth, build)                  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Diagramme réseau

```
Internet
    │
    │ HTTPS TLS 1.2+ (*.a.run.app)
    │ Authentification OIDC obligatoire
    ▼
┌─────────────────────────────┐
│  Cloud Run (Zone publique)   │   ← Seul point d'entrée Internet
│  notes-api-staging           │
│  notes-worker (interne)      │
└──────────────┬──────────────┘
               │ IP privée (VPC peering)
               ▼
┌─────────────────────────────────────────┐
│   VPC staging-vpc — 10.0.0.0/24         │
│   (Zone privée — deny by default)        │
│                                          │
│   Cloud SQL ────── IP privée uniquement  │
│   Secret Manager ─ accès SA autorisés   │
│   Cloud KMS ────── accès SA autorisés   │
└─────────────────────────────────────────┘
```

### 2.3 Choix techniques justifiés

| Choix | Justification |
|---|---|
| Cloud Run vs GKE | Serverless : pas de gestion de nodes, scaling automatique, coût nul à l'arrêt |
| Cloud SQL managé | Backups automatiques, PITR, mises à jour de sécurité gérées par Google |
| Cloud Build | Natif GCP, intégration native Artifact Registry, logs centralisés |
| Terraform | Standard industrie, modules réutilisables staging/prod, state versionné |
| FastAPI + Pydantic | Validation automatique des entrées, typage fort, documentation OpenAPI |
| Gitleaks custom | Règle générique détectant les mots de passe en clair (pas seulement les clés API) |

### 2.4 Séparation des environnements

| Environnement | Projet GCP | State Terraform | Secret |
|---|---|---|---|
| Staging | `projet2-staging` | `gs://tf-state-notes-staging` | `staging-db-password` |
| Prod | `projet2-prod` | `gs://tf-state-notes-prod` | `prod-db-password` |

### 2.5 Maîtrise des coûts

| Service | Coût estimé/mois |
|---|---|
| Cloud Run | ~$0 (free tier : 2M requêtes/mois) |
| Cloud SQL db-f1-micro | ~$7 |
| Artifact Registry | ~$0,10/Go |
| Cloud Build | ~$0 (free tier : 120 min/jour) |
| Secret Manager | ~$0,06/secret |
| **Total estimé** | **< $10/mois** |

---

## 3. Qualité du code

### 3.1 Structure du projet

```
projet2-devsecops/
├── .gitignore                    # Exclut .terraform, *.tfvars, .env
├── .gitleaks.toml                # Règles custom détection secrets
├── cloudbuild.yaml               # Pipeline CI/CD (8 étapes)
├── README.md                     # Documentation principale
├── docs/
│   ├── rapport-securite.md       # Ce document
│   ├── threat-model.md           # Modèle de menaces
│   └── runbook.md                # Procédures d'incident
├── monitoring/
│   ├── alert-iam.json            # Alerte IAM critique
│   ├── alert-auth.json           # Alerte auth suspecte
│   └── alert-build.json          # Alerte pipeline échoué
├── services/
│   ├── api/
│   │   ├── main.py               # API FastAPI
│   │   ├── requirements.txt      # Dépendances
│   │   ├── Dockerfile            # Image non-root
│   │   └── tests/
│   │       └── test_main.py      # 6 tests pytest
│   └── worker/
│       ├── main.py               # Worker scheduler
│       ├── requirements.txt
│       └── Dockerfile            # Image non-root
└── terraform/
    ├── staging/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── backend.tf
    ├── prod/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── backend.tf
    └── modules/
        ├── network/              # VPC + subnet + peering
        ├── database/             # Cloud SQL + backups
        ├── kms/                  # Keyring + clé + rotation
        └── secrets/              # Secret Manager
```

### 3.2 Tests unitaires

6 tests pytest couvrant les cas nominaux et les cas d'erreur :

```python
test_health()                  # GET /health → 200
test_create_note()             # POST /notes → 201
test_list_notes()              # GET /notes → 200 liste
test_delete_note_not_found()   # DELETE /notes/9999 → 404
test_create_note_empty_title() # POST titre vide → 422
test_create_note_title_too_long() # POST titre >200 chars → 422
```

Résultat : **6/6 tests passent** ✅

> 📸 *[Insérer capture de l'output pytest dans le pipeline Cloud Build]*

### 3.3 Sécurité applicative

**Validation des entrées (Pydantic)**

```python
@field_validator("title")
def title_not_empty(cls, v):
    v = v.strip()
    if not v:
        raise ValueError("Le titre ne peut pas être vide")
    if len(v) > 200:
        raise ValueError("Titre trop long (max 200 caractères)")
    return v
```

- Titre : non vide, max 200 caractères
- Contenu : non vide, max 10 000 caractères
- Recherche : max 100 caractères
- Retour HTTP 422 automatique sur validation échouée

**Rate limiting (slowapi)**

| Endpoint | Limite |
|---|---|
| POST /notes | 10 req/min |
| GET /notes | 30 req/min |
| DELETE /notes/{id} | 10 req/min |
| Dépassement | HTTP 429 |

**Gestion des erreurs**

- HTTP 404 : note inexistante
- HTTP 400 : requête invalide
- HTTP 422 : validation échouée
- HTTP 429 : rate limit dépassé

### 3.4 Logs corrélés avec trace-id

Chaque requête reçoit un `trace_id` unique (UUID v4) propagé dans tous les logs :

```json
{
  "time": "2026-05-15T11:00:00Z",
  "level": "INFO",
  "trace_id": "a3f2b1c4-9e8d-4f2a-b1c3-7e9f2a4b8c1d",
  "msg": "Note créée"
}
```

Source du trace-id : header `X-Cloud-Trace-Context` (Cloud Run natif) ou UUID généré.

### 3.5 Conteneurs non-root

Les deux Dockerfiles créent un utilisateur dédié `appuser` :

```dockerfile
RUN useradd -m appuser
USER appuser
```

Détecté et exigé par Semgrep (règle `dockerfile.security.missing-user`).

---

## 4. DevOps & CI/CD

### 4.1 Infrastructure as Code (Terraform)

L'ensemble de l'infrastructure est défini en code, déployable depuis zéro :

```bash
cd terraform/staging
terraform init
terraform apply -var="project_id=projet2-staging"
```

**Ressources provisionnées automatiquement :**

| Module | Ressources créées |
|---|---|
| `network` | VPC, subnet, peering Service Networking, plage IP privée |
| `kms` | Keyring, clé de chiffrement (rotation 90j) |
| `secrets` | Secret Manager (staging-db-password) |
| `database` | Cloud SQL PostgreSQL 15, base `notes`, user `notes-app`, backups PITR |

**State versionné dans GCS :**
```
gs://tf-state-notes-staging/terraform/state/default.tfstate
```

### 4.2 Pipeline CI/CD (Cloud Build)

Déclenché automatiquement sur chaque push vers `main`.

```
┌──────────────────────────────────────────────────────┐
│                  cloudbuild.yaml                       │
│                                                        │
│  Étape 1 : pytest ──────────── Tests unitaires        │
│  Étape 2 : Gitleaks ─────────── Secrets dans le code  │
│  Étape 3 : Semgrep ──────────── SAST applicatif       │
│  Étape 4 : Checkov ──────────── Scan IaC Terraform    │
│  Étape 5 : docker build ─────── Construction image    │
│  Étape 6 : Trivy ────────────── CVE critiques image   │
│  Étape 7 : docker push ──────── Artifact Registry     │
│  Étape 8 : gcloud run deploy ── Cloud Run staging     │
└──────────────────────────────────────────────────────┘
```

**Politique "fail build" :**

| Outil | Condition de blocage |
|---|---|
| pytest | Au moins 1 test échoué |
| Gitleaks | Au moins 1 secret détecté |
| Semgrep | Au moins 1 finding bloquant |
| Checkov | Violations critiques IaC |
| Trivy | Au moins 1 CVE CRITICAL dans l'image |

> 📸 *[Insérer capture d'un pipeline complet au vert]*

### 4.3 Déploiement reproductible

**Staging :**
```bash
terraform apply -var="project_id=projet2-staging"
# → Déploie l'infra complète depuis zéro
```

**Déclenchement CI/CD :**
```bash
git push origin main
# → Pipeline déclenché automatiquement via webhook GitHub
```

### 4.4 Rollback

```bash
# Lister les révisions Cloud Run
gcloud run revisions list --service=notes-api-staging \
  --region=europe-west1 --project=projet2-staging

# Basculer vers la révision stable
gcloud run services update-traffic notes-api-staging \
  --to-revisions=REVISION_STABLE=100 \
  --region=europe-west1 --project=projet2-staging
```

**RTO rollback applicatif : < 2 minutes**

---

## 5. Contrôles de sécurité obligatoires

> Pour chaque contrôle : (a) preuve de config, (b) test négatif, (c) logs, (d) correction.

---

### Contrôle 1 — Séparation des identités

**Configuration**

| Identité | Type | Usage |
|---|---|---|
| Compte développeur | Humain (MFA) | Accès console GCP, git push |
| `notes-api-sa` | Service Account | Exécution API uniquement |
| `notes-worker-sa` | Service Account | Exécution Worker uniquement |
| `cloudbuild-sa` | Service Account | Pipeline CI/CD uniquement |
| `terraform-sa` | Service Account | Provisionnement IaC uniquement |

Aucun compte humain utilisé dans les SA. Aucun SA utilisé pour accès console.

> 📸 *[Insérer capture gcloud iam service-accounts list --project=projet2-staging]*

**Test négatif** : Tentative de connexion console avec un SA → refusée par GCP (les SA ne peuvent pas s'authentifier sur la console).

---

### Contrôle 2 — Least Privilege

**Configuration**

```
roles/cloudsql.client               → notes-api-sa
roles/secretmanager.secretAccessor  → notes-api-sa
roles/logging.logWriter             → notes-worker-sa
roles/artifactregistry.writer       → cloudbuild-sa
roles/run.admin                     → cloudbuild-sa
roles/iam.serviceAccountUser        → cloudbuild-sa
roles/logging.logWriter             → cloudbuild-sa
roles/storage.objectViewer          → cloudbuild-sa
```

> 📸 *[Insérer capture gcloud projects get-iam-policy projet2-staging]*

**Test négatif** : Tentative d'accès à Secret Manager avec `notes-worker-sa` (rôle `logging.logWriter` uniquement) → refus 403.

---

### Contrôle 3 — Secrets Manager

**Configuration**
- Mot de passe DB stocké dans Secret Manager (`staging-db-password`)
- Aucun secret en clair dans le code, les variables CI ou les images Docker
- Gitleaks configuré avec règle custom (`.gitleaks.toml`) dans le pipeline

**Test négatif** : Ajout de `DB_PASSWORD = "SuperSecret123!"` dans le code → pipeline bloqué par Gitleaks (voir Attaque 2).

```bash
gcloud secrets list --project=projet2-staging
# staging-db-password   ENABLED
```

> 📸 *[Insérer capture gcloud secrets list]*

---

### Contrôle 4 — Segmentation réseau

**Configuration**
- VPC dédié `staging-vpc`, subnet `10.0.0.0/24`
- Cloud SQL : IP privée uniquement (peering VPC — `servicenetworking.googleapis.com`)
- Cloud Run : `--no-allow-unauthenticated`
- Org policy GCP bloquant `allUsers` sur Cloud Run

**Test négatif** : Accès direct à Cloud SQL depuis Internet → impossible (pas d'IP publique).

> 📸 *[Insérer capture Cloud SQL → onglet Connexions → IP privée uniquement]*

---

### Contrôle 5 — Chiffrement

**Transit**
```bash
echo | openssl s_client -connect ${SERVICE_URL#https://}:443 2>/dev/null \
  | openssl x509 -noout -dates -subject
# notBefore=Apr 20 08:34:47 2026 GMT
# notAfter=Jul 13 08:34:46 2026 GMT
# subject=CN = *.a.run.app
```

**Stockage**
```bash
gcloud kms keys list \
  --keyring=staging-notes-keyring \
  --location=europe-west1 \
  --project=projet2-staging
# db-encryption-key   GOOGLE_SYMMETRIC_ENCRYPTION   ENABLED   rotation: 7776000s
```

> 📸 *[Insérer capture openssl + gcloud kms keys list]*

---

### Contrôle 6 — Authentification robuste

**Configuration**
- Cloud Run : `--no-allow-unauthenticated` (OIDC obligatoire)
- Tokens OIDC Google : TTL ~1 heure, rotation automatique
- Comptes admin GCP : MFA activé

**Tests**
```bash
# Sans token → 403
curl -o /dev/null -s -w "%{http_code}\n" https://notes-api-staging-jkx6b532qq-ew.a.run.app/health
# 403

# Avec token → 200
TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer $TOKEN" \
  -o /dev/null -s -w "%{http_code}\n" https://notes-api-staging-jkx6b532qq-ew.a.run.app/health
# 200
```

> 📸 *[Insérer capture des deux curl (403 et 200)]*

---

### Contrôle 7 — Validation d'entrée

**Configuration**
- Validation Pydantic sur tous les champs (voir §3.3)
- Rate limiting slowapi (voir §3.3)
- Requêtes SQL paramétrées (détectées par Semgrep si non respectées)
- Recherche : longueur max 100 caractères

**Test négatif**
```bash
# Titre vide → 422
curl -X POST https://notes-api-staging-jkx6b532qq-ew.a.run.app/notes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"","content":"test"}'
# {"detail":[{"msg":"Le titre ne peut pas être vide"}]}
```

> 📸 *[Insérer capture du curl retournant 422]*

---

### Contrôle 8 — Logs & Audit

**Configuration**

Logs JSON structurés avec trace-id sur Cloud Run :
```json
{"time":"2026-05-15T11:00:00Z","level":"INFO","trace_id":"a3f2b1c4-...","msg":"Note créée"}
```

Audit trail GCP activé (Cloud Audit Logs) sur toutes les opérations IAM/Admin.

```bash
gcloud logging read "resource.type=cloud_run_revision" \
  --limit=10 --project=projet2-staging \
  --format="table(timestamp,jsonPayload.trace_id,jsonPayload.msg)"
```

> 📸 *[Insérer capture Cloud Logging avec les logs structurés et trace-id]*

---

### Contrôle 9 — Alerting

3 alertes Cloud Monitoring configurées :

| Alerte | Filtre | Période |
|---|---|---|
| IAM critique | `protoPayload.methodName="SetIamPolicy"` | 300s |
| Auth suspecte | `httpRequest.status>=401 AND <=403` | 300s |
| Pipeline échoué | `resource.type="build" severity="ERROR"` | 300s |

```bash
gcloud alpha monitoring policies list \
  --project=projet2-staging \
  --format="table(displayName,enabled)"
# Alerte IAM critique       True
# Alerte auth suspecte      True
# Alerte pipeline echoue    True
```

> 📸 *[Insérer capture gcloud monitoring policies list]*

---

### Contrôle 10 — CI/CD sécurisé

Pipeline 8 étapes avec "fail build" sur :

| Outil | Cible | Exit-code |
|---|---|---|
| pytest | Tests unitaires | 1 si échec |
| Gitleaks | Secrets dans le code | 1 si secret trouvé |
| Semgrep | Injections, sécurité | 1 si finding bloquant |
| Checkov | IaC Terraform | configurable |
| Trivy | CVE CRITICAL image | 1 si CVE trouvée |

> 📸 *[Insérer capture du pipeline Cloud Build avec toutes les étapes au vert]*

---

### Contrôle 11 — IaC reproductible

```bash
# Staging
cd terraform/staging && terraform init && terraform apply -var="project_id=projet2-staging"

# Prod
cd terraform/prod && terraform init && terraform apply -var="project_id=projet2-prod"
```

State stocké dans GCS versionné. Modules réutilisables pour staging et prod.

> 📸 *[Insérer capture terraform apply avec "Apply complete! Resources: X added"]*

---

### Contrôle 12 — Backups & Restore

**Configuration**
```bash
gcloud sql backups list --instance=staging-notes-db --project=projet2-staging
```

| Paramètre | Valeur |
|---|---|
| Backups automatiques | Activés (02h00 UTC) |
| PITR | Activé |
| Rétention | 7 jours |
| RPO | 1 heure |
| RTO | 15 minutes |

**Procédure de restauration** : documentée dans `docs/runbook.md` — Scénario 3.

> 📸 *[Insérer capture gcloud sql backups list]*

---

### Contrôle 13 — Stockage objet

**Configuration**
```bash
gcloud storage buckets describe gs://notes-archives-projet2-staging \
  --format="value(iamConfiguration.publicAccessPrevention)"
# enforced
```

**Test négatif** : Accès public après activation `publicAccessPrevention` → HTTP 403 (voir Attaque 6).

> 📸 *[Insérer capture gcloud storage buckets describe avec "enforced"]*

---

### Contrôle 14 — Posture baseline (optionnel)

Non implémentée (nécessite Security Command Center Premium — hors budget académique).

---

## 6. Modèle de menaces

### 6.1 Acteurs

| Acteur | Type | Niveau de confiance |
|---|---|---|
| Développeur | Humain interne (MFA) | Élevé |
| Pipeline Cloud Build | Machine (`cloudbuild-sa`) | Élevé — limité aux droits SA |
| `notes-api-sa` | Machine | Moyen — 2 rôles uniquement |
| `notes-worker-sa` | Machine | Faible — logging uniquement |
| Utilisateur API | Externe | Non confiance — OIDC obligatoire |
| Attaquant externe | Externe | Zéro confiance |

### 6.2 Analyse STRIDE

| Catégorie | Menace | Vecteur | Contrôle en place | Statut |
|---|---|---|---|---|
| **Spoofing** | Usurpation identité API | Token OIDC volé | TTL 1h, signature Google | ✅ Mitigé |
| **Tampering** | Image modifiée | CVE dans dépendance | Trivy bloque CRITICAL | ✅ Mitigé |
| **Repudiation** | Action non tracée | Absence de logs | Cloud Logging + trace-id | ✅ Mitigé |
| **Info Disclosure** | Secret dans le repo | Commit avec credential | Gitleaks (bloquant) | ✅ Mitigé |
| **Info Disclosure** | Bucket public | ACL mal configurée | publicAccessPrevention | ✅ Mitigé |
| **Info Disclosure** | Injection SQL | Input non validé | Semgrep SAST + paramétrage | ✅ Mitigé |
| **Denial of Service** | Flood requêtes | Surcharge API | Rate limiting slowapi | ✅ Mitigé |
| **Elevation of Privilege** | IAM trop large | SA avec rôle owner | Least privilege + audit | ✅ Mitigé |
| **Supply chain** | Dépendance vulnérable | pip install | Trivy exit-code 1 CRITICAL | ✅ Mitigé |
| **Exposure** | Service public | allUsers Cloud Run | `--no-allow-unauthenticated` + org policy | ✅ Mitigé |

### 6.3 Flux de données sensibles

```
Utilisateur ──[OIDC token HTTPS]──► Cloud Run API
Cloud Run   ──[IP privée VPC]────► Cloud SQL (mot de passe via Secret Manager)
Cloud Build ──[SA token]─────────► Artifact Registry (push image)
Cloud Build ──[SA token]─────────► Cloud Run (deploy)
Terraform   ──[SA key]───────────► GCP APIs (provisionnement infra)
```

---

## 7. Démonstration des attaques

> Format pour chaque attaque : capture avant → log → commit correctif → re-test après.

---

### Attaque 1 — Supply chain (dépendance vulnérable)

**Vecteur** : Dépendance `python-jose==3.3.0` contenant CVE-2024-33663 (CRITICAL).

**AVANT**

`services/api/requirements.txt` :
```
python-jose==3.3.0
```

Résultat Trivy — étape 6 du pipeline :
```
python-jose │ CVE-2024-33663 │ CRITICAL │ 3.3.0 │ Fixed: 3.4.0
```
Pipeline bloqué : `ERROR: build step 5 "aquasec/trivy" failed: exit status 1`

> 📸 *[Insérer capture Trivy bloqué avec CVE-2024-33663]*

**Log Cloud Build correspondant** :
```
Total: 1 (CRITICAL: 1)
Finished Step #5
ERROR: build step 5 "aquasec/trivy" failed: step exited with non-zero status: 1
```

> 📸 *[Insérer capture log Cloud Build étape Trivy]*

**Correctif** — commit `fix: mise a jour python-jose 3.3.0 -> 3.4.0 (CVE-2024-33663)` :
```
python-jose==3.4.0
```

**APRÈS**

```
Total: 0 (CRITICAL: 0)
```
Pipeline passé ✅

> 📸 *[Insérer capture Trivy 0 CVE + pipeline au vert]*

---

### Attaque 2 — Fuite de secret CI/CD

**Vecteur** : Mot de passe en clair committé dans le code source.

**AVANT**

Code ajouté dans `services/api/main.py` :
```python
DB_PASSWORD = "SuperSecret123!"
```

Résultat Gitleaks — étape 2 :
```
Finding:     DB_PASSWORD = "SuperSecret123!"
RuleID:      generic-password-assignment
File:        services/api/main.py
Line:        94
Commit:      014a590d...
```
Pipeline bloqué : `ERROR: build step 1 "zricethezav/gitleaks" failed: exit status 1`

> 📸 *[Insérer capture Gitleaks bloqué avec le finding]*

**Log correspondant** :
```
11:16AM WRN leaks found: 1
Finished Step #1
ERROR: build step 1 "zricethezav/gitleaks" failed: step exited with non-zero status: 1
```

> 📸 *[Insérer capture log Cloud Build étape Gitleaks]*

**Correctif** — commit `fix: suppression secret en clair (demo gitleaks)` :
- Suppression de `DB_PASSWORD = "SuperSecret123!"`
- Le vrai mot de passe reste dans Secret Manager

**APRÈS**

```
11:16AM INF 0 leaks found
```
Pipeline passé ✅

> 📸 *[Insérer capture Gitleaks 0 leaks + pipeline au vert]*

---

### Attaque 3 — IAM trop permissif

**Vecteur** : Service account avec `roles/owner` — accès total au projet.

**AVANT**

```bash
gcloud projects add-iam-policy-binding projet2-staging \
  --member="serviceAccount:notes-api-sa@projet2-staging.iam.gserviceaccount.com" \
  --role="roles/owner"

# Accès non autorisé : lister tous les secrets
gcloud secrets list --project=projet2-staging \
  --impersonate-service-account=notes-api-sa@projet2-staging.iam.gserviceaccount.com
# → Liste tous les secrets du projet
```

> 📸 *[Insérer capture de la liste des secrets accessible avec le SA owner]*

**Log Cloud Audit correspondant** :
```
SetIamPolicy sur projet2-staging par développeur@groupe.com
→ Alerte Cloud Monitoring "Alerte IAM critique" déclenchée
```

> 📸 *[Insérer capture de l'alerte IAM dans Cloud Monitoring]*

**Correctif** :
```bash
gcloud projects remove-iam-policy-binding projet2-staging \
  --member="serviceAccount:notes-api-sa@projet2-staging.iam.gserviceaccount.com" \
  --role="roles/owner"
```

**APRÈS**

```
ROLE                                MEMBERS
roles/cloudsql.client               serviceAccount:notes-api-sa@...
roles/secretmanager.secretAccessor  serviceAccount:notes-api-sa@...
```
Least privilege restauré ✅

> 📸 *[Insérer capture IAM policy avec uniquement les 2 rôles légitimes]*

---

### Attaque 4 — Exposition publique involontaire

**Vecteur** : Service Cloud Run rendu accessible sans authentification.

**AVANT**

```bash
gcloud run services add-iam-policy-binding notes-api-staging \
  --region=europe-west1 \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --project=projet2-staging

curl -o /dev/null -s -w "Sans token : %{http_code}\n" https://notes-api-staging-jkx6b532qq-ew.a.run.app/health
# Sans token : 200
```

> 📸 *[Insérer capture du curl retournant 200 sans token]*

**Log correspondant** :
```
httpRequest.status: 200
httpRequest.requestUrl: /health
httpRequest.remoteIp: [IP publique attaquant]
```

> 📸 *[Insérer capture Cloud Logging avec requête 200 sans token]*

**Correctif** :
```bash
gcloud run services remove-iam-policy-binding notes-api-staging \
  --region=europe-west1 \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --project=projet2-staging
```

Note : l'org policy GCP (`constraints/iam.allowedPolicyMemberTypes`) bloque structurellement `allUsers` sur Cloud Run — défense en profondeur.

**APRÈS**

```bash
curl -o /dev/null -s -w "Sans token : %{http_code}\n" https://notes-api-staging-jkx6b532qq-ew.a.run.app/health
# Sans token : 403
```
Accès refusé ✅

> 📸 *[Insérer capture du curl retournant 403]*

---

### Attaque 5 — Injection SQL

**Vecteur** : Endpoint utilisant la concaténation directe dans une requête SQL.

**AVANT**

Code ajouté dans `services/api/main.py` :
```python
@app.get("/notes/search")
def search_notes_vulnerable(q: str):
    conn = psycopg2.connect("dbname=notes user=notes-app")
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM notes WHERE title LIKE '%{q}%'")
    return cur.fetchall()
```

Résultat Semgrep — étape 3 — **3 règles bloquantes** :
```
python.lang.security.audit.formatted-sql-query        [BLOCKING] ligne 101
python.lang.security.audit.sqli.psycopg-sqli          [BLOCKING] ligne 101
python.sqlalchemy.security.sqlalchemy-execute-raw-query [BLOCKING] ligne 101
```
Pipeline bloqué : `ERROR: build step 2 "python:3.11-slim" failed: exit status 1`

> 📸 *[Insérer capture Semgrep bloqué avec les 3 règles]*

**Log correspondant** :
```
Ran 296 rules on 12 files: 3 findings.
Finished Step #2
ERROR: build step 2 "python:3.11-slim" failed: step exited with non-zero status: 1
```

> 📸 *[Insérer capture log Cloud Build étape Semgrep]*

**Correctif** — commit `fix: remplacement SQLi par recherche securisee` :
```python
@app.get("/notes/search")
def search_notes(q: str, request: Request):
    if len(q) > 100:
        raise HTTPException(status_code=400, detail="Requête trop longue")
    results = [n for n in notes_db.values() if q.lower() in n["title"].lower()]
    return results
```

**APRÈS**

```
Ran 296 rules on 12 files: 0 findings.
```
Pipeline passé ✅

> 📸 *[Insérer capture Semgrep 0 findings + pipeline au vert]*

---

### Attaque 6 — Exfiltration via stockage objet

**Vecteur** : Bucket GCS avec données sensibles rendu public par erreur de configuration.

**AVANT**

```bash
gsutil mb -l europe-west1 gs://notes-archives-projet2-staging
echo '{"notes":[{"id":1,"title":"Confidentiel","content":"Données sensibles"}]}' \
  > /tmp/export.json
gsutil cp /tmp/export.json gs://notes-archives-projet2-staging/
gsutil iam ch allUsers:objectViewer gs://notes-archives-projet2-staging

curl -o /dev/null -s -w "Acces public : %{http_code}\n" \
  https://storage.googleapis.com/notes-archives-projet2-staging/export.json
# Acces public : 200
```

> 📸 *[Insérer capture du curl retournant 200 avec les données du fichier]*

**Log Cloud Audit correspondant** :
```
storage.objects.get sur notes-archives-projet2-staging/export.json
principal: allUsers (non authentifié)
```

> 📸 *[Insérer capture Cloud Audit Log accès anonyme au bucket]*

**Correctif** :
```bash
gcloud storage buckets update gs://notes-archives-projet2-staging \
  --uniform-bucket-level-access \
  --public-access-prevention
```

**APRÈS**

```bash
curl -o /dev/null -s -w "Acces public : %{http_code}\n" \
  https://storage.googleapis.com/notes-archives-projet2-staging/export.json
# Acces public : 403
```
Exfiltration bloquée ✅

> 📸 *[Insérer capture du curl retournant 403]*

---

## 8. Observabilité et alerting

### 8.1 Logs centralisés

Tous les services envoient leurs logs à Cloud Logging en format JSON structuré.

**Consultation :**
```bash
gcloud logging read "resource.type=cloud_run_revision" \
  --limit=20 --project=projet2-staging \
  --format="table(timestamp,jsonPayload.trace_id,jsonPayload.level,jsonPayload.msg)"
```

> 📸 *[Insérer capture Cloud Logging avec plusieurs entrées et trace-ids visibles]*

### 8.2 Audit trail IAM

```bash
gcloud logging read \
  'protoPayload.methodName="SetIamPolicy"' \
  --limit=5 --project=projet2-staging
```

> 📸 *[Insérer capture Cloud Audit Logs avec les opérations IAM]*

### 8.3 Alertes Cloud Monitoring

```bash
gcloud alpha monitoring policies list \
  --project=projet2-staging \
  --format="table(displayName,enabled)"
```

```
DISPLAY_NAME              ENABLED
Alerte IAM critique       True
Alerte auth suspecte      True
Alerte pipeline echoue    True
```

> 📸 *[Insérer capture console Cloud Monitoring avec les 3 alertes actives]*

---

## 9. Guide de démo

### 9.1 Ordre de présentation recommandé

```
1. Introduction (2 min)
   → Présenter l'architecture (diagramme §2.1)
   → Expliquer les 2 microservices et le pipeline

2. Pipeline en action (3 min)
   → Faire un git push en live
   → Montrer les 8 étapes s'exécuter dans Cloud Build
   → Montrer le déploiement Cloud Run au vert

3. Attaque Supply chain (3 min)
   → Montrer capture Trivy bloqué (CVE-2024-33663)
   → Montrer capture après correction (0 CVE)

4. Attaque Fuite secret (3 min)
   → Montrer capture Gitleaks bloqué
   → Montrer Secret Manager comme alternative

5. Attaque Injection SQL (3 min)
   → Montrer capture Semgrep bloqué (3 règles)
   → Montrer le correctif avec requête paramétrée

6. Attaque Exposition publique (2 min)
   → Montrer curl 200 sans token (avant)
   → Montrer curl 403 (après)

7. Attaque Exfiltration stockage (2 min)
   → Montrer curl 200 sur bucket public (avant)
   → Montrer curl 403 après publicAccessPrevention

8. Observabilité (2 min)
   → Montrer Cloud Logging avec trace-id
   → Montrer les 3 alertes Cloud Monitoring

9. Questions (5 min)
```

### 9.2 Commandes à préparer pour la démo live

```bash
# Déclencher le pipeline
git commit --allow-empty -m "demo: trigger pipeline" && git push origin main

# Appel API avec token
TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL=$(gcloud run services describe notes-api-staging \
  --region=europe-west1 --project=projet2-staging --format='value(status.url)')

curl -H "Authorization: Bearer $TOKEN" https://notes-api-staging-jkx6b532qq-ew.a.run.app/health
curl -H "Authorization: Bearer $TOKEN" -X POST https://notes-api-staging-jkx6b532qq-ew.a.run.app/notes \
  -H "Content-Type: application/json" \
  -d '{"title":"Demo","content":"Note de demonstration"}'

# Voir les logs en live
gcloud logging tail "resource.type=cloud_run_revision" --project=projet2-staging

# Voir les alertes
gcloud alpha monitoring policies list --project=projet2-staging
```

---

## 10. Conclusion et résidus de risque

### 10.1 Bilan des contrôles

| Critère SCL | Points | Réalisé |
|---|---|---|
| Architecture (diagrammes, choix, séparation env, coûts) | 20 | ✅ |
| Sécurité (14 contrôles, threat model) | 30 | ✅ |
| DevOps & CI/CD (IaC, pipeline, scans, rollback) | 15 | ✅ |
| Documentation (README, runbook, threat model, guide démo) | 15 | ✅ |
| Démo (6 attaques, logs, alertes) | 10 | ✅ |
| Qualité du code (tests, validation, trace-id) | 10 | ✅ |
| **Total** | **100** | **✅** |

### 10.2 Résidus de risque acceptés

| Risque résiduel | Justification |
|---|---|
| Pas de WAF dédié (Cloud Armor) | Hors budget crédits académiques |
| Pas de rotation automatique secrets | Rotation manuelle documentée runbook |
| PITR limité à 7 jours | Suffisant pour le contexte académique |
| Pas de Security Command Center | Licence Premium payante |
| Checkov en soft-fail | Certains checks nécessitent droits supplémentaires |
| Pas de signature Cosign | Complexité hors scope du délai imparti |

### 10.3 Améliorations possibles en production

- Activer Cloud Armor (WAF) devant Cloud Run
- Mettre en place la rotation automatique des secrets (Secret Manager + Cloud Functions)
- Signer les images avec Cosign (SLSA Level 2)
- Ajouter un gating manuel avant déploiement prod
- Activer Security Command Center pour posture baseline CIS
- Mettre en place des tests d'intégration (Karate/Postman)
