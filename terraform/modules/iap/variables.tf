variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "cloud_run_service_name" {
  type = string
}

variable "allowed_users" {
  type        = list(string)
  description = "Liste d'identités IAM autorisées via IAP, format \"user:email\""
}
