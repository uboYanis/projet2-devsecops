# Projet 2 — DevSecOps avancé : CI/CD & IaC policy-gated

API de gestion de notes avec pipeline CI/CD durci sur GCP.

## Architecture

```
                        ┌─────────────────────────────────────────┐
                        │             GCP projet2-staging          │
                        │                                          │
  GitHub ──push──► Cloud Build                                     │
                        │                                          │
                        │  1. Tests unitaires (pytest)             │
                        │  2. Scan secrets (Gitleaks)              │
                        │  3. SAST (Semgrep)                       │
                        │  4. Scan IaC (Checkov)                   │
                        │  5. Build image Docker                   │
                        │  6. Scan image (Trivy)                   │
                        │  7. Push ──────────► Artifact Registry   │
                        │  8. Deploy ─────────► Cloud Run          │
                        │                           │              │
                        │                    Secret Manager        │
                        │                    KMS (chiffrement)     │
                        │                    Cloud SQL (PostgreSQL) │
                        │                    Cloud Logging          │
                        │                    Cloud Monitoring       │
                        └─────────────────────────────────────────┘
```

## Services

| Service | Description |
|---|---|
| `notes-api-staging` | API REST FastAPI — CRUD de notes |
| `notes-worker` | Worker Python — archivage notes >30j |

## Prérequis

- `gcloud` CLI configuré
- `terraform` >= 1.5
- `docker`
- Compte GCP avec projets `projet2-staging` et `projet2-prod`

## Déploiement

### 1. Cloner le repo

```bash
git clone https://github.com/uboYanis/projet2-devsecops.git
cd projet2-devsecops
```

### 2. Configurer les credentials Terraform

```bash
cp /chemin/vers/terraform-sa.json ~/.config/gcloud/keys/terraform-sa-staging.json
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/keys/terraform-sa-staging.json
```

### 3. Créer le secret DB

```bash
echo -n "MonMotDePasse!" | gcloud secrets create staging-db-password \
  --data-file=- \
  --replication-policy=automatic \
  --project=projet2-staging
```

### 4. Déployer l'infra staging

```bash
cd terraform/staging
terraform init
terraform apply -var="project_id=projet2-staging"
```

### 5. Connecter Cloud Build à GitHub

Console GCP → Cloud Build → Déclencheurs → Connecter un dépôt → GitHub

### 6. Pousser le code

```bash
git push origin main
```

Le pipeline CI/CD se déclenche automatiquement.

## Tests locaux

```bash
cd services/api
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Vérifications rapides

```bash
# Statut des services Cloud Run
gcloud run services list --region=europe-west1 --project=projet2-staging

# Logs en temps réel
gcloud logging read "resource.type=cloud_run_revision" \
  --limit=50 --project=projet2-staging

# Appel API avec token
TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL=$(gcloud run services describe notes-api-staging \
  --region=europe-west1 --project=projet2-staging --format='value(status.url)')
curl -H "Authorization: Bearer $TOKEN" $SERVICE_URL/health
```

## Matrice des permissions

| Service Account | Rôle | Justification |
|---|---|---|
| `notes-api-sa` | `secretmanager.secretAccessor` | Lire le mot de passe DB |
| `notes-api-sa` | `cloudsql.client` | Se connecter à Cloud SQL |
| `notes-worker-sa` | `logging.logWriter` | Écrire les logs |
| `cloudbuild-sa` | `artifactregistry.writer` | Pusher les images |
| `cloudbuild-sa` | `run.admin` | Déployer sur Cloud Run |
| `cloudbuild-sa` | `iam.serviceAccountUser` | Associer les SA aux services |
| `cloudbuild-sa` | `logging.logWriter` | Écrire les logs de build |
