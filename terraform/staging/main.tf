provider "google" {
  project = var.project_id
  region  = var.region
}

module "network" {
  source = "../modules/network"
  env    = "staging"
  region = var.region
}

module "kms" {
  source = "../modules/kms"
  env    = "staging"
  region = var.region
}

module "secrets" {
  source = "../modules/secrets"
  env    = "staging"
}

data "google_secret_manager_secret_version" "db_password" {
  secret = module.secrets.db_password_id
}

module "database" {
  source                 = "../modules/database"
  env                    = "staging"
  region                 = var.region
  vpc_id                 = module.network.vpc_id
  db_password            = data.google_secret_manager_secret_version.db_password.secret_data
  private_vpc_connection = module.network.private_vpc_connection
}
