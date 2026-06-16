# Guide Terraform — Projet 2 DevSecOps

## Structure des fichiers

```
terraform/
├── staging/          ← environnement staging
│   ├── main.tf       ← appelle les modules
│   ├── variables.tf
│   └── backend.tf    ← stockage du state dans GCS
├── prod/             ← même structure, autre projet GCP
└── modules/
    ├── network/      ← VPC + subnet + peering
    ├── kms/          ← clé de chiffrement
    ├── secrets/      ← Secret Manager
    └── database/     ← Cloud SQL PostgreSQL
```

---

## Ce que Terraform crée, module par module

### 1. `module "network"` — le réseau privé

Terraform crée :
- Un **VPC** dédié (`staging-vpc`) avec `auto_create_subnetworks = false` — aucun réseau automatique
- Un **subnet** (`staging-subnet`, plage `10.0.0.0/24`)
- Une **plage IP réservée** pour les services Google (nécessaire pour Cloud SQL en IP privée)
- Un **peering VPC** avec `servicenetworking.googleapis.com` — permet à Cloud SQL d'avoir une IP privée dans ce VPC

> Sans ce peering, Cloud SQL ne peut pas avoir d'IP privée et serait exposé sur Internet.

---

### 2. `module "kms"` — chiffrement

Terraform crée :
- Un **keyring** (`staging-notes-keyring`) dans `europe-west1`
- Une **clé de chiffrement** (`db-encryption-key`) avec rotation automatique tous les **90 jours** (`7776000s`)

---

### 3. `module "secrets"` — Secret Manager

Terraform crée :
- Un **secret** (`staging-db-password`) dans Secret Manager pour stocker le mot de passe de la base de données

Le mot de passe n'est jamais écrit dans le code. Il est lu au moment du déploiement via :

```hcl
data "google_secret_manager_secret_version" "db_password" {
  secret = module.secrets.db_password_id
}
```

---

### 4. `module "database"` — Cloud SQL PostgreSQL

Terraform crée :
- Une **instance Cloud SQL** PostgreSQL 15 (`staging-notes-db`)
  - IP privée uniquement (`ipv4_enabled = false`) — inaccessible depuis Internet
  - Backups automatiques quotidiens à 02h00 UTC
  - PITR activé (Point-In-Time Recovery) — restauration à la minute près
  - Rétention 7 jours
- Une **base de données** `notes`
- Un **utilisateur** `notes-app` avec le mot de passe lu depuis Secret Manager

---

## Comment déployer

### Étape 1 — Initialiser

Télécharge les providers GCP et configure le backend GCS.

```bash
cd terraform/staging
terraform init
```

---

### Étape 2 — Planifier (sans rien modifier)

Affiche la liste de toutes les ressources qui vont être créées, modifiées ou supprimées. Aucune action n'est effectuée sur GCP.

```bash
terraform plan -var="project_id=projet2-staging"
```

Exemple de sortie :
```
Plan: 8 to add, 0 to change, 0 to destroy.
```

**Test négatif** : lancer `plan` sans avoir configuré les credentials GCP → erreur d'authentification :
```
Error: google: could not find default credentials
```

---

### Étape 3 — Appliquer (créer l'infrastructure)

Terraform demande une confirmation (`yes`), puis crée toutes les ressources dans le bon ordre en respectant les dépendances.

```bash
terraform apply -var="project_id=projet2-staging"
```

Exemple de sortie :
```
Apply complete! Resources: 8 added, 0 changed, 0 destroyed.
```

**Test négatif** : lancer `apply` avec un `project_id` inexistant sur GCP → erreur :
```
Error: Error creating Network: googleapi: Error 403: ... project not found
```

---

### Étape 4 — Vérifier l'état

Affiche toutes les ressources actuellement gérées par Terraform et leur état réel sur GCP.

```bash
terraform show
```

---

### Étape 5 — Détruire l'infrastructure

Supprime toutes les ressources créées. Utile pour libérer les crédits GCP après les tests.

```bash
terraform destroy -var="project_id=projet2-staging"
```

**Test négatif** : modifier manuellement une ressource dans la console GCP (ex. changer le nom du subnet), puis relancer `apply` → Terraform détecte la divergence et recrée la ressource pour retrouver l'état attendu.

---

## Le state Terraform

Le fichier `backend.tf` configure où Terraform stocke son état :

```hcl
terraform {
  backend "gcs" {
    bucket = "tf-state-notes-staging"
    prefix = "terraform/state"
  }
}
```

Le **state** est le fichier qui dit à Terraform ce qui existe déjà sur GCP. Il est stocké dans un bucket GCS versionné pour que toute l'équipe partage le même état et évite les conflits.

| Rôle du state | Explication |
|---|---|
| Suivi des ressources | Terraform sait ce qu'il a créé et ce qu'il doit mettre à jour |
| Détection des dérives | Si quelqu'un modifie GCP manuellement, `terraform plan` le détecte |
| Collaboration | Tout le groupe travaille avec le même state partagé sur GCS |
| Versionnement | Le bucket GCS est versionné — on peut revenir à un state antérieur |

---

## Ordre de création automatique

Terraform résout les dépendances tout seul grâce aux références entre modules :

```
network  →  database  (la DB a besoin du VPC ID pour l'IP privée)
secrets  →  database  (le mot de passe est lu depuis Secret Manager)
kms      →  (indépendant, créé en parallèle)
```

Vous n'avez pas à vous préoccuper de l'ordre — Terraform crée d'abord le réseau, lit le secret, puis crée la base de données avec les deux.

---

## Séparation staging / prod

Les deux environnements sont identiques en structure mais isolés :

| Paramètre | Staging | Prod |
|---|---|---|
| Projet GCP | `projet2-staging` | `projet2-prod` |
| State GCS | `tf-state-notes-staging` | `tf-state-notes-prod` |
| Secret DB | `staging-db-password` | `prod-db-password` |
| Préfixe ressources | `staging-*` | `prod-*` |

Pour déployer en prod :

```bash
cd terraform/prod
terraform init
terraform apply -var="project_id=projet2-prod"
```

---

## Commandes utiles

```bash
# Voir les ressources gérées
terraform state list

# Inspecter une ressource précise
terraform state show module.database.google_sql_database_instance.postgres

# Valider la syntaxe des fichiers sans contacter GCP
terraform validate

# Formater les fichiers .tf selon le standard HashiCorp
terraform fmt -recursive
```