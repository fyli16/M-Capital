variable "environment" {
  type        = string
  description = "Deployment environment (staging|prod)."
}
variable "region" {
  type    = string
  default = "us-east-1"
}
variable "azs" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}
variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

# Image tag deployed (usually the git SHA); repos are created here.
variable "image_tag" {
  type    = string
  default = "latest"
}

# App configuration
variable "llm_provider" {
  type    = string
  default = "openai"
}
variable "data_provider" {
  type    = string
  default = "live"
}
variable "sec_user_agent" {
  type    = string
  default = ""
}
variable "openai_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

# Environment sizing knobs
variable "single_nat_gateway" {
  type    = bool
  default = true
}
variable "db_instance_class" {
  type    = string
  default = "db.t4g.medium"
}
variable "db_multi_az" {
  type    = bool
  default = false
}
variable "db_deletion_protection" {
  type    = bool
  default = false
}
variable "redis_node_type" {
  type    = string
  default = "cache.t4g.small"
}
variable "redis_replicas" {
  type    = number
  default = 0
}
variable "api_desired_count" {
  type    = number
  default = 2
}
variable "worker_min_count" {
  type    = number
  default = 1
}
variable "worker_max_count" {
  type    = number
  default = 10
}
variable "certificate_arn" {
  type    = string
  default = ""
}
