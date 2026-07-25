# Partial backend — supply values per environment:
#   terraform init -backend-config=env/staging.backend.hcl
terraform {
  backend "s3" {
    key     = "aegis/terraform.tfstate"
    encrypt = true
    # bucket, dynamodb_table, region provided via -backend-config
  }
}
