variable "aws_region" {
  description = "AWS region"
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  default     = "t3.small"
}

variable "db_instance_class" {
  description = "RDS instance class"
  default     = "db.t3.micro"
}

variable "db_username" {
  description = "PostgreSQL username"
  default     = "postgres"
}

variable "db_password" {
  description = "PostgreSQL password"
  sensitive   = true
}

variable "key_pair_name" {
  description = "EC2 key pair name (must exist in AWS Academy)"
}

variable "auth0_domain" {
  description = "Auth0 tenant domain (e.g. your-tenant.us.auth0.com)"
}

variable "auth0_audience" {
  description = "Auth0 API audience"
  default     = "https://bite-finops-api"
}
