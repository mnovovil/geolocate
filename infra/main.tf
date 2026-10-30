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

  # Pre-built footer scan (scripts/build_file_index.py). Only valid for the release it was built
  # from: for any other path the CLI falls back to scanning the whole folder.
  file_index        = jsondecode(file("${path.module}/overture_file_index.json"))
  file_index_active = trimsuffix(local.file_index.source, "/") == trimsuffix(var.overture_buildings_path, "/")
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
    overture_file_index     = local.file_index_active ? local.file_index : null
  })
}
