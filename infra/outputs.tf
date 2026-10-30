output "config_path" {
  description = "Path of the generated .geolocate.json."
  value       = local_sensitive_file.geolocate_config.filename
}

output "overture_buildings_path" {
  description = "Overture buildings release the config points at."
  value       = var.overture_buildings_path
}

output "file_index_active" {
  description = "Whether overture_file_index.json matches the configured release. If false, rebuild it (see docs/reference.md) or every point scans the whole folder."
  value       = local.file_index_active
}
