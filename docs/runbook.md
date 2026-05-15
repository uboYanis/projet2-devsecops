# Runbook — Projet 2 DevSecOps

## Scénario 1 — Pipeline CI/CD échoué

### Symptômes
- Alerte Cloud Monitoring "Alerte pipeline echoue" déclenchée
- Build en erreur dans Console GCP → Cloud Build → Historique

### Diagnostic

```bash
# Voir les logs du dernier build
gcloud builds list --limit=5 --project=projet2-staging

# Détail du build échoué
gcloud builds describe BUILD_ID --project=projet2-staging
```

### Actions selon l'étape en échec

| Étape | Cause probable | Action |
|---|---|---|
| Tests unitaires | Régression code | Corriger le test ou le code, re-pousser |
| Gitleaks | Secret dans le code | Supprimer le secret, utiliser Secret Manager |
| Semgrep | Faille SAST détectée | Corriger le code (injection, XSS, etc.) |
| Checkov | IaC risquée | Corriger le fichier Terraform |
| Trivy | CVE critique dans l'image | Mettre à jour la dépendance vulnérable |
| Cloud Run deploy | Droits insuffisants | Vérifier les rôles du SA `cloudbuild-sa` |

---

## Scénario 2 — Secret compromis

### Symptômes
- Alerte IAM suspecte déclenchée
- Activité anormale dans Cloud Logging

### Procédure de rotation

```bash
# 1. Générer un nouveau mot de passe
NEW_PASSWORD=$(openssl rand -base64 24)

# 2. Ajouter une nouvelle version du secret
echo -n "$NEW_PASSWORD" | gcloud secrets versions add staging-db-password \
  --data-file=- \
  --project=projet2-staging

# 3. Désactiver l'ancienne version
OLD_VERSION=$(gcloud secrets versions list staging-db-password \
  --project=projet2-staging \
  --format='value(name)' \
  --filter='state=ENABLED' \
  --sort-by='~createTime' \
  --limit=2 | tail -1)

gcloud secrets versions disable $OLD_VERSION \
  --secret=staging-db-password \
  --project=projet2-staging

# 4. Mettre à jour le mot de passe Cloud SQL
gcloud sql users set-password notes-app \
  --instance=staging-notes-db \
  --password="$NEW_PASSWORD" \
  --project=projet2-staging

# 5. Redémarrer le service Cloud Run pour recharger le secret
gcloud run services update notes-api-staging \
  --region=europe-west1 \
  --project=projet2-staging \
  --no-traffic

# 6. Vérifier que le service répond
TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL=$(gcloud run services describe notes-api-staging \
  --region=europe-west1 --project=projet2-staging --format='value(status.url)')
curl -H "Authorization: Bearer $TOKEN" $SERVICE_URL/health
```

---

## Scénario 3 — Rollback

### Symptômes
- Régression détectée après déploiement
- Erreurs dans Cloud Logging sur la révision en cours

### Procédure de rollback

```bash
# 1. Lister les révisions disponibles
gcloud run revisions list \
  --service=notes-api-staging \
  --region=europe-west1 \
  --project=projet2-staging \
  --format='table(name,status.conditions[0].status,spec.containers[0].image)'

# 2. Identifier la dernière révision stable (avant le déploiement problématique)
PREVIOUS_REVISION=notes-api-staging-XXXXX  # remplacer par le nom réel

# 3. Basculer 100% du trafic vers la révision précédente
gcloud run services update-traffic notes-api-staging \
  --region=europe-west1 \
  --project=projet2-staging \
  --to-revisions=$PREVIOUS_REVISION=100

# 4. Vérifier
TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL=$(gcloud run services describe notes-api-staging \
  --region=europe-west1 --project=projet2-staging --format='value(status.url)')
curl -H "Authorization: Bearer $TOKEN" $SERVICE_URL/health

# 5. Investiguer la révision défaillante dans les logs
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.revision_name=$PREVIOUS_REVISION" \
  --limit=50 \
  --project=projet2-staging
```

### RPO / RTO

| Paramètre | Valeur |
|---|---|
| RPO (perte de données max) | 1 heure (PITR Cloud SQL) |
| RTO (temps de restauration max) | 15 minutes (rollback Cloud Run) |
| Rétention backups DB | 7 jours |
