resource "google_sql_database_instance" "postgres" {
  name             = "${var.env}-notes-db"
  database_version = "POSTGRES_15"
  region           = var.region

  depends_on = [var.private_vpc_connection]

  settings {
    tier = "db-f1-micro"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "02:00"
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.vpc_id
    }
  }

  deletion_protection = false
}

resource "google_sql_database" "notes" {
  name     = "notes"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app" {
  name     = "notes-app"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

output "db_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}
