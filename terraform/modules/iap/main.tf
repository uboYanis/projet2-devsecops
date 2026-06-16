resource "google_project_service" "iap" {
  project            = var.project_id
  service            = "iap.googleapis.com"
  disable_on_destroy = false
}

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_cloud_run_service_iam_member" "iap_invoker" {
  project  = var.project_id
  location = var.region
  service  = var.cloud_run_service_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-iap.iam.gserviceaccount.com"

  depends_on = [google_project_service.iap]
}

resource "google_iap_web_cloud_run_service_iam_member" "allowed_users" {
  for_each = toset(var.allowed_users)

  project  = var.project_id
  location = var.region
  cloud_run_service_name = var.cloud_run_service_name
  role     = "roles/iap.httpsResourceAccessor"
  member   = each.value

  depends_on = [google_project_service.iap]
}
