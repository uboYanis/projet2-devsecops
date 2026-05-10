resource "google_kms_key_ring" "notes" {
  name     = "${var.env}-notes-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "db_key" {
  name            = "db-encryption-key"
  key_ring        = google_kms_key_ring.notes.id
  rotation_period = "7776000s"

  lifecycle {
    prevent_destroy = false
  }
}

output "crypto_key_id" {
  value = google_kms_crypto_key.db_key.id
}

output "keyring_name" {
  value = google_kms_key_ring.notes.name
}
