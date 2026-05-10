terraform {
  backend "gcs" {
    bucket = "tf-state-notes-staging"
    prefix = "terraform/state"
  }
}
