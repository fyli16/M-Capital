provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project     = "aegis-capital"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
