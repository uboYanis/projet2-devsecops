resource "google_compute_network" "vpc" {
  name                    = "${var.env}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${var.env}-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
}

# Plage d'adresses réservée pour les services Google (Cloud SQL private IP)
resource "google_compute_global_address" "private_ip_range" {
  name          = "${var.env}-private-ip-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

# Peering VPC avec Google Service Networking
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}

# Subnet dédié /28 pour le VPC Access Connector (Cloud Run → Cloud SQL)
resource "google_compute_subnetwork" "connector_subnet" {
  name          = "${var.env}-connector-subnet"
  ip_cidr_range = "10.0.1.0/28"
  region        = var.region
  network       = google_compute_network.vpc.id
}

resource "google_vpc_access_connector" "connector" {
  name          = "${var.env}-vpc-connector"
  region        = var.region
  subnet {
    name = google_compute_subnetwork.connector_subnet.name
  }
  machine_type  = "e2-micro"
  min_instances = 2
  max_instances = 3
}

output "vpc_id" {
  value = google_compute_network.vpc.id
}

output "vpc_self_link" {
  value = google_compute_network.vpc.self_link
}

output "private_vpc_connection" {
  value = google_service_networking_connection.private_vpc_connection.id
}

output "vpc_connector_name" {
  value = google_vpc_access_connector.connector.name
}
