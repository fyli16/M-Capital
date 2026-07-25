# Secrets module: generates/stores app secrets in AWS Secrets Manager.

variable "name" { type = string }
variable "openai_api_key" {
  type      = string
  sensitive = true
  default   = ""
}
variable "tags" {
  type    = map(string)
  default = {}
}

resource "random_password" "db" {
  length  = 32
  special = false # keep RDS/URL-safe
}

resource "random_password" "jwt" {
  length  = 48
  special = true
}

resource "aws_secretsmanager_secret" "jwt" {
  name = "${var.name}/jwt-secret"
  tags = var.tags
}
resource "aws_secretsmanager_secret_version" "jwt" {
  secret_id     = aws_secretsmanager_secret.jwt.id
  secret_string = random_password.jwt.result
}

resource "aws_secretsmanager_secret" "openai" {
  name = "${var.name}/openai-api-key"
  tags = var.tags
}
resource "aws_secretsmanager_secret_version" "openai" {
  secret_id     = aws_secretsmanager_secret.openai.id
  secret_string = var.openai_api_key
}

output "db_password" {
  value     = random_password.db.result
  sensitive = true
}
output "jwt_secret_arn" { value = aws_secretsmanager_secret.jwt.arn }
output "openai_secret_arn" { value = aws_secretsmanager_secret.openai.arn }
