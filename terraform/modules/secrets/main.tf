resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.env}-db-password"
  replication {
    auto {}
  }
}

output "db_password_id" {
  value = google_secret_manager_secret.db_password.secret_id
}
