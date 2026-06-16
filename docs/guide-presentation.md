# Guide de présentation — Projet 2 DevSecOps

## Ordre recommandé (environ 25 minutes)

---

## 1. Introduction — Architecture (2 min)

**Ce qu'on dit :**
- On a développé une API REST de gestion de notes déployée sur GCP
- Elle est composée de 2 microservices : `notes-api` (FastAPI) et `notes-worker` (archivage)
- Tout le déploiement passe par un pipeline CI/CD de 8 étapes qui bloque automatiquement si une faille est détectée

**Ce qu'on montre :**
- Le diagramme d'architecture dans `docs/rapport-securite.md` section 2.1
- La structure des fichiers du projet (README.md)

---

## 2. Démonstration de l'API (2 min)

**Ce qu'on dit :**
- L'API est déployée sur Cloud Run et nécessite une authentification OIDC
- Sans token, l'accès est refusé

**Commandes à lancer en live :**

```bash
# Sans token → 403 (accès refusé)
curl -o /dev/null -s -w "Sans token : %{http_code}\n" \
  https://notes-api-staging-jkx6b532qq-ew.a.run.app/health

# Avec token → 200 (accès autorisé)
TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer $TOKEN" \
  -o /dev/null -s -w "Avec token : %{http_code}\n" \
  https://notes-api-staging-jkx6b532qq-ew.a.run.app/health

# Créer une note
curl -H "Authorization: Bearer $TOKEN" \
  -X POST https://notes-api-staging-jkx6b532qq-ew.a.run.app/notes \
  -H "Content-Type: application/json" \
  -d '{"title":"Demo prof","content":"Note de demonstration"}'
```

---

## 3. Tests unitaires (1 min)

**Ce qu'on dit :**
- 6 tests pytest couvrent les cas nominaux et les cas d'erreur
- Ils sont lancés automatiquement à chaque push dans le pipeline

**Commande à lancer en live :**

```bash
cd services/api
python3 -m pytest tests/ -v
```

**Résultat attendu :** 6 tests verts en quelques secondes.

---

## 4. Pipeline CI/CD — Vue d'ensemble (2 min)

**Ce qu'on dit :**
- À chaque `git push`, Cloud Build déclenche automatiquement 8 étapes
- Si une étape échoue, le déploiement est bloqué — l'image vulnérable n'arrive jamais sur Cloud Run

**Ce qu'on montre :**
- Console GCP → Cloud Build → Historique → cliquer sur le dernier build
- Montrer les 8 étapes au vert : pytest, Gitleaks, Semgrep, Checkov, Docker build, Trivy, push, deploy

---

## 5. Attaque 1 — Supply chain (CVE dépendance) (3 min)

**Ce qu'on dit :**
- La dépendance `python-jose==3.3.0` contient une CVE CRITICAL (CVE-2024-33663)
- Trivy scanne l'image Docker et bloque le build si une CVE critique est détectée

**Ce qu'on montre :**
- Capture d'écran du build bloqué par Trivy avec le message :
```
python-jose │ CVE-2024-33663 │ CRITICAL │ Fixed: 3.4.0
ERROR: build step 5 "aquasec/trivy" failed: exit status 1
```
- Capture d'écran après correctif (`python-jose==3.4.0`) : `Total: 0 (CRITICAL: 0)` ✅

---

## 6. Attaque 2 — Fuite de secret (2 min)

**Ce qu'on dit :**
- Un développeur a committé un mot de passe en clair dans le code
- Gitleaks scanne tout le dépôt Git et bloque le build immédiatement

**Ce qu'on montre :**
- Capture d'écran Gitleaks bloqué :
```
Finding:     DB_PASSWORD = "SuperSecret123!"
RuleID:      generic-password-assignment
ERROR: build step 1 "zricethezav/gitleaks" failed: exit status 1
```
- Montrer Secret Manager dans la console GCP : le vrai mot de passe est stocké là, jamais dans le code

**Commande :**
```bash
gcloud secrets list --project=projet2-staging
```

---

## 7. Attaque 3 — Injection SQL (3 min)

**Ce qu'on dit :**
- Un endpoint utilisait la concaténation directe dans une requête SQL
- Semgrep détecte ce pattern et bloque le build avec 3 règles simultanées

**Ce qu'on montre :**
- Le code vulnérable (dans le rapport) :
```python
cur.execute(f"SELECT * FROM notes WHERE title LIKE '%{q}%'")
```
- Capture d'écran Semgrep bloqué avec 3 findings
- Le correctif : recherche en mémoire sans SQL
- Les tests d'injection dans `test_main.py` qui passent tous au vert :

```bash
cd services/api
python3 -m pytest tests/test_main.py -v -k "sqli"
```

---

## 8. Attaque 4 — IAM trop permissif (2 min)

**Ce qu'on dit :**
- Le service account `notes-api-sa` avait le rôle `roles/owner` (accès total au projet)
- L'alerte Cloud Monitoring "Alerte IAM critique" s'est déclenchée automatiquement

**Ce qu'on montre :**
- Capture d'écran de l'alerte IAM dans Cloud Monitoring
- La politique IAM actuelle avec least privilege (uniquement 2 rôles) :
```
roles/cloudsql.client              → notes-api-sa
roles/secretmanager.secretAccessor → notes-api-sa
```

---

## 9. Attaque 5 — Exposition publique (2 min)

**Ce qu'on dit :**
- Le service a été rendu public par erreur (`allUsers` ajouté)
- Après correction, sans token → 403

**Ce qu'on montre en live :**
```bash
# Sans token → 403
curl -o /dev/null -s -w "Sans token : %{http_code}\n" \
  https://notes-api-staging-jkx6b532qq-ew.a.run.app/health
```

---

## 10. Attaque 6 — Exfiltration stockage (1 min)

**Ce qu'on dit :**
- Un bucket GCS a été rendu public par erreur de configuration
- Après activation de `publicAccessPrevention` → accès bloqué en 403

**Ce qu'on montre :**
- Capture d'écran avant : `curl` retourne 200 avec les données
- Capture d'écran après : `curl` retourne 403

---

## 11. Observabilité (2 min)

**Ce qu'on dit :**
- Chaque requête génère un log JSON structuré avec un `trace_id` unique
- 3 alertes Cloud Monitoring surveillent les événements critiques

**Commandes à lancer en live :**

```bash
# Logs en temps réel
gcloud logging tail "resource.type=cloud_run_revision" \
  --project=projet2-staging

# Alertes actives
gcloud alpha monitoring policies list \
  --project=projet2-staging \
  --format="table(displayName,enabled)"
```

**Résultat attendu :**
```
Alerte IAM critique       True
Alerte auth suspecte      True
Alerte pipeline echoue    True
```

---

## 12. Infrastructure Terraform (1 min)

**Ce qu'on dit :**
- Toute l'infra est définie en code Terraform, déployable depuis zéro en une commande
- State versionné dans GCS pour travailler en équipe

**Commande :**
```bash
cd terraform/staging
terraform show
```

---

## Résumé à dire en conclusion (1 min)

> "À chaque commit, notre pipeline bloque automatiquement les CVE critiques, les secrets en clair, les injections SQL et les mauvaises configurations IaC. Le déploiement n'a lieu que si les 8 étapes passent. L'infrastructure est entièrement reproductible via Terraform et les accès sont contrôlés par least privilege. Les 3 alertes Cloud Monitoring assurent la détection en temps réel."

---

## Checklist avant la démo

- [ ] `gcloud auth login` effectué avec le bon compte
- [ ] Terminal 1 prêt avec les commandes curl copiées
- [ ] Console GCP ouverte sur Cloud Build → Historique
- [ ] Console GCP ouverte sur Cloud Monitoring → Alertes
- [ ] Captures d'écran des builds bloqués prêtes (attaques 1 à 6)
- [ ] `python3 -m pytest tests/ -v` lancé une fois pour vérifier que tout passe
