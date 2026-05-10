terraform {
  backend "gcs" {
    bucket = "tf-state-notes-prod"
    prefix = "terraform/state"
  }
}
