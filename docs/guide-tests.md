# Guide de tests — Projet 2 DevSecOps

## 1. Tests unitaires (pytest)

### Prérequis

```bash
cd services/api
pip install -r requirements.txt
```

### Lancer les tests

```bash
python3 -m pytest tests/ -v
```

### Résultat attendu

```
tests/test_main.py::test_health                     PASSED
tests/test_main.py::test_create_note                PASSED
tests/test_main.py::test_list_notes                 PASSED
tests/test_main.py::test_delete_note_not_found      PASSED
tests/test_main.py::test_create_note_empty_title    PASSED
tests/test_main.py::test_create_note_title_too_long PASSED

6 passed in X.XXs
```

---

### Détail de chaque test

#### `test_health`
**Ce qu'il fait** : appelle `GET /health` et vérifie que l'API répond `{"status": "ok"}` avec un code HTTP 200. Sert à confirmer que le service est démarré et répond correctement.

**Test négatif** : supprimer ou renommer la route `/health` dans `main.py` → le test retourne `FAILED` avec `AssertionError: assert 404 == 200`.

---

#### `test_create_note`
**Ce qu'il fait** : envoie `POST /notes` avec un titre et un contenu valides, vérifie que le code HTTP est 201 (créé) et que le champ `title` dans la réponse correspond bien à ce qui a été envoyé.

**Test négatif** : changer `assert r.status_code == 201` en `assert r.status_code == 200` dans le test → `FAILED` car l'API renvoie bien 201, pas 200.

---

#### `test_list_notes`
**Ce qu'il fait** : appelle `GET /notes` et vérifie que la réponse est une liste JSON (même vide). Confirme que l'endpoint de listing fonctionne et retourne le bon type de données.

**Test négatif** : dans `main.py`, remplacer `return list(notes_db.values())` par `return {}` → le test `assert isinstance(r.json(), list)` échoue car un dictionnaire est retourné à la place d'une liste.

---

#### `test_delete_note_not_found`
**Ce qu'il fait** : tente de supprimer la note avec l'ID `9999` (qui n'existe pas) et vérifie que l'API répond bien 404. Confirme que les erreurs métier sont correctement gérées.

**Test négatif** : dans `main.py`, retirer le `raise HTTPException(status_code=404, ...)` et retourner `{}` à la place → le test `assert r.status_code == 404` échoue car l'API renvoie 200.

---

#### `test_create_note_empty_title`
**Ce qu'il fait** : envoie `POST /notes` avec un titre vide `""` et vérifie que l'API répond 422 (validation échouée). Confirme que la validation Pydantic rejette les entrées invalides.

**Test négatif** : supprimer le `@field_validator("title")` dans `main.py` → Pydantic accepte le titre vide, l'API répond 201, le test `assert r.status_code == 422` échoue.

---

#### `test_create_note_title_too_long`
**Ce qu'il fait** : envoie `POST /notes` avec un titre de 201 caractères (limite max = 200) et vérifie que l'API répond 422. Confirme que la limite de longueur est appliquée.

**Test négatif** : dans `main.py`, changer `if len(v) > 200` en `if len(v) > 500` → un titre de 201 caractères passe la validation, l'API répond 201, le test `assert r.status_code == 422` échoue.

---

## 2. Tests manuels de l'API (Cloud Run — staging)

> **⚠️ Avec IAP activé (`--iap`)**, l'accès navigateur passe désormais par un login Google (redirection vers l'écran de consentement) au lieu d'un token brut dans l'URL. Les commandes `curl` ci-dessous, basées sur `gcloud auth print-identity-token`, sont à **revalider après l'activation d'IAP** : IAP peut exiger un token dont l'`audience` correspond au client OAuth IAP (et non un identity-token générique). Si les appels `curl` échouent avec un 401/403 alors que le compte est bien autorisé (`roles/iap.httpsResourceAccessor`), utiliser :
> ```bash
> export TOKEN=$(gcloud auth print-identity-token --audiences=<IAP_CLIENT_ID>)
> ```
> où `<IAP_CLIENT_ID>` se trouve dans la console GCP → Sécurité → Identity-Aware Proxy → service `notes-api-staging` → "Détails OAuth".

### Prérequis : récupérer l'URL et le token

```bash
export TOKEN=$(gcloud auth print-identity-token)
export URL=$(gcloud run services describe notes-api-staging --region=europe-west1 --project=projet2-staging --format='value(status.url)')
echo $URL
```

> Le token expire après 1 heure. Relancer `export TOKEN=$(gcloud auth print-identity-token)` si besoin.

---

### Appels curl

#### Health check
**Ce qu'il fait** : vérifie que le service Cloud Run est vivant et répond.
```bash
curl -H "Authorization: Bearer $TOKEN" "$URL/health"
# Attendu → {"status":"ok"}
```
**Test négatif** : appeler sans token → 403 Forbidden
```bash
curl "$URL/health"
# Attendu → 403
```

---

#### Créer une note
**Ce qu'il fait** : insère une note en base PostgreSQL (Cloud SQL) via l'API et retourne l'objet créé avec son ID.
```bash
curl -X POST "$URL/notes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Ma note","content":"Contenu test"}'
# Attendu → {"id":1,"title":"Ma note","content":"Contenu test"}
```
**Test négatif** : envoyer sans le champ `content` → `422 Unprocessable Entity`
```bash
curl -X POST "$URL/notes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Ma note"}'
# Attendu → 422
```

---

#### Lister les notes
**Ce qu'il fait** : retourne toutes les notes stockées en base sous forme de liste JSON.
```bash
curl -H "Authorization: Bearer $TOKEN" "$URL/notes"
# Attendu → [{"id":1,"title":"Ma note","content":"Contenu test"}]
```
**Test négatif** : appeler sur une base vide → liste vide `[]` (comportement normal, pas d'erreur).

---

#### Supprimer une note
**Ce qu'il fait** : supprime la note par son ID en base et confirme la suppression.
```bash
curl -X DELETE -H "Authorization: Bearer $TOKEN" "$URL/notes/1"
# Attendu → {"message":"supprimée"}
```
**Test négatif** : supprimer un ID inexistant → 404
```bash
curl -X DELETE -H "Authorization: Bearer $TOKEN" "$URL/notes/9999"
# Attendu → {"detail":"Note non trouvée"}
```

---

#### Titre vide
**Ce qu'il fait** : démontre que la validation Pydantic bloque les titres vides avant toute écriture en base.
```bash
curl -X POST "$URL/notes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"","content":"test"}'
# Attendu → 422 + message "Le titre ne peut pas être vide"
```
**Pourquoi c'est important** : sans cette validation, un attaquant pourrait insérer des données corrompues en base.

---

#### Titre trop long
**Ce qu'il fait** : démontre que la limite de 200 caractères est appliquée.
```bash
curl -X POST "$URL/notes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"'"$(python3 -c "print('A'*201)")"'","content":"test"}'
# Attendu → 422 + message "Titre trop long (max 200 caractères)"
```
**Test négatif** : envoyer exactement 200 caractères → 201 (accepté, c'est la limite exacte).

---

#### Recherche
**Ce qu'il fait** : filtre les notes dont le titre contient le mot-clé (requête paramétrée PostgreSQL, insensible à la casse).
```bash
curl -H "Authorization: Bearer $TOKEN" "$URL/notes/search?q=note"
# Attendu → liste des notes dont le titre contient "note"
```
**Test négatif** : requête de plus de 100 caractères → 400
```bash
curl -H "Authorization: Bearer $TOKEN" "$URL/notes/search?q=$(python3 -c "print('x'*101)")"
# Attendu → {"detail":"Requête trop longue"}
```

---

## 3. Tests de sécurité locaux

### Gitleaks — détection de secrets

**Ce qu'il fait** : scanne tout le dépôt Git à la recherche de secrets en clair (mots de passe, tokens, clés API) selon les règles de `.gitleaks.toml`.

```bash
# Depuis la racine du projet
gitleaks detect --source . --config .gitleaks.toml -v
# Attendu → 0 leaks found
```

**Test négatif** : ajouter temporairement un secret dans le code, puis relancer :
```bash
# 1. Ajouter dans services/api/main.py :
#    DB_PASSWORD = "SuperSecret123!"

# 2. Relancer Gitleaks
gitleaks detect --source . --config .gitleaks.toml -v
# Attendu → Finding: DB_PASSWORD = "SuperSecret123!" — exit code 1
```

---

### Semgrep — analyse statique (SAST)

**Ce qu'il fait** : analyse le code Python à la recherche de failles de sécurité (injections SQL, mauvaises pratiques, code dangereux).

```bash
pip install semgrep
semgrep --config=auto services/ --error
# Attendu → 0 findings
```

**Test négatif** : ajouter une requête SQL vulnérable dans `main.py` :
```python
# Ajouter cet endpoint vulnérable :
@app.get("/notes/vuln")
def vuln(q: str):
    import psycopg2
    conn = psycopg2.connect("dbname=notes")
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM notes WHERE title LIKE '%{q}%'")
    return cur.fetchall()
```
```bash
semgrep --config=auto services/ --error
# Attendu → 3 findings bloquants (formatted-sql-query, psycopg-sqli, sqlalchemy-execute-raw-query)
#           exit code 1
```

---

### Checkov — scan IaC Terraform

**Ce qu'il fait** : vérifie que les fichiers Terraform respectent les bonnes pratiques de sécurité (chiffrement activé, pas d'accès public, backups configurés, etc.).

```bash
pip install checkov
checkov -d terraform/ --compact
```

**Test négatif** : dans `terraform/modules/database/main.tf`, passer `enabled = false` sur les backups :
```hcl
backup_configuration {
  enabled = false
}
```
```bash
checkov -d terraform/ --compact
# Attendu → FAILED pour la règle CKV_GCP_14 (backup non activé)
```

---

### Trivy — scan de l'image Docker

**Ce qu'il fait** : scanne l'image Docker construite à la recherche de CVE (failles connues) dans les dépendances Python et les paquets système.

```bash
cd services/front && npm ci && npm run build && cd ../..
docker build -f services/api/Dockerfile -t notes-api:test .

docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity CRITICAL notes-api:test
# Attendu → Total: 0 (CRITICAL: 0)
```

**Test négatif** : ajouter la version vulnérable dans `requirements.txt` :
```
python-jose==3.3.0
```
```bash
docker build -f services/api/Dockerfile -t notes-api:vuln .
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity CRITICAL notes-api:vuln
# Attendu → python-jose | CVE-2024-33663 | CRITICAL — exit code 1
```

---

## 4. Tests Docker

### Builder et lancer l'image API

**Ce qu'il fait** : construit l'image de production et vérifie qu'elle démarre correctement.

```bash
cd services/front && npm ci && npm run build && cd ../..
docker build -f services/api/Dockerfile -t notes-api:test .
docker run -p 8080:8080 notes-api:test
curl http://localhost:8080/health
# Attendu → {"status":"ok"}
# Ouvrir http://localhost:8080/ dans un navigateur → l'UI React doit s'afficher (pas d'IAP en local)
```

**Test négatif** : modifier `CMD` dans le `Dockerfile` avec un mauvais port :
```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9999"]
```
```bash
curl http://localhost:8080/health
# Attendu → curl: (7) Failed to connect (le service écoute sur 9999, pas 8080)
```

---

### Vérifier que le conteneur tourne en non-root

**Ce qu'il fait** : confirme que le processus dans le conteneur s'exécute avec l'utilisateur `appuser` et non `root`. Un conteneur root peut compromettre l'hôte en cas d'évasion de conteneur.

```bash
docker run --rm --entrypoint whoami notes-api:test
# Attendu → appuser
```

**Test négatif** : supprimer les lignes `RUN adduser -D appuser` et `USER appuser` du `Dockerfile`, reconstruire :
```bash
docker build -f services/api/Dockerfile -t notes-api:root .
docker run --rm --entrypoint whoami notes-api:root
# Attendu → root  ← faille de sécurité
```

---

### Builder l'image worker

**Ce qu'il fait** : vérifie que le worker se construit et démarre sans erreur.

```bash
docker build -t notes-worker:test ./services/worker
docker run notes-worker:test
# Attendu → log JSON "Worker démarré"
```

---

## 5. Test du pipeline CI/CD complet

**Ce qu'il fait** : déclenche automatiquement les 10 étapes de sécurité sur Cloud Build à chaque push sur `main`. Le pipeline bloque le déploiement si l'une des étapes échoue.

```bash
git commit --allow-empty -m "test: trigger pipeline"
git push origin main
```

Suivre l'exécution dans la console GCP → Cloud Build → Historique.

| # | Étape | Outil | Condition de blocage |
|---|---|---|---|
| 1 | Tests unitaires | pytest | 1 test échoué |
| 2 | Scan secrets | Gitleaks | 1 secret détecté |
| 3 | SAST | Semgrep | 1 finding bloquant |
| 4 | Scan IaC | Checkov | violations critiques |
| 5 | Build frontend | npm (Vite) | erreur de build |
| 6 | Build image API | Docker | erreur de build |
| 7 | Scan CVE image | Trivy | 1 CVE CRITICAL |
| 8 | Push image | Docker | erreur de push |
| 9 | Récupération IP Cloud SQL | Terraform output | erreur de lecture d'état |
| 10 | Déploiement (IAP activé) | Cloud Run | erreur de déploiement |

**Test négatif (démo pipeline bloqué)** : ajouter `python-jose==3.3.0` dans `requirements.txt` et pousser → le pipeline s'arrête à l'étape 7 (Trivy) avec `exit status 1`. Les étapes suivantes ne s'exécutent pas — l'image vulnérable n'est jamais déployée.

---

## 6. Tests sur Cloud Run (staging)

> Depuis l'activation d'IAP (`--iap`), un utilisateur ouvrant l'URL du service dans un navigateur est automatiquement redirigé vers l'écran de connexion Google, puis n'a accès à l'UI que s'il fait partie de `allowed_users` (module Terraform `iap`, `roles/iap.httpsResourceAccessor`). Les comptes non autorisés reçoivent un 403 d'IAP avant même d'atteindre le code de l'application. Les appels `curl`/OIDC ci-dessous restent utiles pour les tests automatisés (CI, scripts) qui n'ont pas de navigateur.

### Authentification OIDC obligatoire

**Ce qu'il fait** : vérifie que le service Cloud Run refuse les requêtes sans token d'authentification Google (OIDC). Seuls les utilisateurs/services authentifiés peuvent accéder à l'API.

```bash
TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL=$(gcloud run services describe notes-api-staging \
  --region=europe-west1 \
  --project=projet2-staging \
  --format='value(status.url)')

# Test négatif : sans token → doit être refusé
curl -o /dev/null -s -w "Sans token : %{http_code}\n" https://notes-api-staging-jkx6b532qq-ew.a.run.app/health
# Attendu → 403

# Test positif : avec token → doit fonctionner
curl -H "Authorization: Bearer $TOKEN" \
  -o /dev/null -s -w "Avec token : %{http_code}\n" https://notes-api-staging-jkx6b532qq-ew.a.run.app/health
# Attendu → 200
```

**Pourquoi c'est important** : sans `--no-allow-unauthenticated`, n'importe qui sur Internet pourrait appeler l'API sans s'authentifier.

---

### Créer une note sur le service déployé

```bash
curl -H "Authorization: Bearer $TOKEN" \
  -X POST https://notes-api-staging-jkx6b532qq-ew.a.run.app/notes \
  -H "Content-Type: application/json" \
  -d '{"title":"Demo","content":"Note de demonstration"}'
# Attendu → {"id":1,"title":"Demo","content":"Note de demonstration"}
```

---

## 7. Vérifications de l'infrastructure

### Statut des services Cloud Run
**Ce qu'il fait** : liste les services déployés et leur statut (actif, en erreur).
```bash
gcloud run services list --region=europe-west1 --project=projet2-staging
# Attendu → notes-api-staging  READY
```

### Lister les secrets
**Ce qu'il fait** : confirme que le mot de passe DB est bien dans Secret Manager et non dans le code.
```bash
gcloud secrets list --project=projet2-staging
# Attendu → staging-db-password  ENABLED
```

### Lister les clés KMS
**Ce qu'il fait** : vérifie que la clé de chiffrement est bien créée et active.
```bash
gcloud kms keys list \
  --keyring=staging-notes-keyring \
  --location=europe-west1 \
  --project=projet2-staging
# Attendu → db-encryption-key  ENABLED  rotation: 7776000s
```

### Vérifier les alertes Cloud Monitoring
**Ce qu'il fait** : confirme que les 3 alertes de sécurité sont actives (IAM, auth suspecte, pipeline échoué).
```bash
gcloud alpha monitoring policies list \
  --project=projet2-staging \
  --format="table(displayName,enabled)"
# Attendu :
# Alerte IAM critique       True
# Alerte auth suspecte      True
# Alerte pipeline echoue    True
```

### Logs en temps réel
**Ce qu'il fait** : affiche les logs structurés JSON avec trace-id au fil des requêtes. Permet de corréler chaque action avec son identifiant de trace.
```bash
gcloud logging tail "resource.type=cloud_run_revision" \
  --project=projet2-staging
# Attendu → lignes JSON avec "trace_id", "level", "msg"
```