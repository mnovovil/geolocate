output "config_path" {
  description = "Path of the generated .geolocate.json."
  value       = local_sensitive_file.geolocate_config.filename
}

output "overture_buildings_path" {
  description = "Overture buildings release the config points at."
  value       = var.overture_buildings_path
}
