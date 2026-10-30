# Writes the local, git-ignored .geolocate.json read by src/config.py.
# The keys below are a contract with src/config.py — change both sides together.
#
# NOTE: the Terraform state (terraform.tfstate) holds these values, including any credentials,
# in plain text. It is git-ignored; keep it that way.

terraform {
  required_version = ">= 1.3"

  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

locals {
  config_path = abspath("${path.module}/../.geolocate.json")
}

resource "local_sensitive_file" "geolocate_config" {
  filename        = local.config_path
  file_permission = "0600"

  content = jsonencode({
    overture_buildings_path = var.overture_buildings_path
    s3_region               = var.s3_region
    aws_access_key_id       = var.aws_access_key_id
    aws_secret_access_key   = var.aws_secret_access_key
    aws_session_token       = var.aws_session_token
    search_radius_m         = var.search_radius_m
  })
}
