variable "overture_buildings_path" {
  description = "S3 folder of the Overture buildings GeoParquet release to query."
  type        = string
  default     = "s3://overturemaps-us-west-2/release/2026-10-21.0/theme=buildings/type=building/"
}

variable "s3_region" {
  description = "AWS region of the Overture bucket."
  type        = string
  default     = "us-west-2"
}

variable "aws_access_key_id" {
  description = "Optional AWS access key ID. Leave empty to read the public bucket anonymously."
  type        = string
  default     = ""
  sensitive   = true
}

variable "aws_secret_access_key" {
  description = "Optional AWS secret access key."
  type        = string
  default     = ""
  sensitive   = true
}

variable "aws_session_token" {
  description = "Optional AWS session token (for temporary credentials)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "search_radius_m" {
  description = "Radius in metres for the nearest-building fallback."
  type        = number
  default     = 100

  validation {
    condition     = var.search_radius_m > 0
    error_message = "search_radius_m must be positive."
  }
}
