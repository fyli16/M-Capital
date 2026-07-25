locals {
  name = "aegis-${var.environment}"
  tags = { Environment = var.environment }
}

# ---- Container registries ---------------------------------------------------

resource "aws_ecr_repository" "api" {
  name                 = "${local.name}/api-gateway"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = local.tags
}
resource "aws_ecr_repository" "worker" {
  name                 = "${local.name}/agent-worker"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = local.tags
}
resource "aws_ecr_repository" "perf" {
  name                 = "${local.name}/performance-worker"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = local.tags
}
resource "aws_ecr_repository" "migrate" {
  name                 = "${local.name}/migrate"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = local.tags
}

# ---- Network ----------------------------------------------------------------

module "network" {
  source             = "./modules/network"
  name               = local.name
  cidr               = var.vpc_cidr
  azs                = var.azs
  single_nat_gateway = var.single_nat_gateway
  tags               = local.tags
}

module "alb" {
  source            = "./modules/alb"
  name              = local.name
  vpc_id            = module.network.vpc_id
  public_subnet_ids = module.network.public_subnet_ids
  certificate_arn   = var.certificate_arn
  tags              = local.tags
}

# Shared application security group (ECS tasks). ALB reaches api on the container port.
resource "aws_security_group" "app" {
  name_prefix = "${local.name}-app-"
  vpc_id      = module.network.vpc_id

  ingress {
    description     = "ALB to api container"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [module.alb.alb_sg_id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  lifecycle { create_before_destroy = true }
  tags = local.tags
}

# ---- Secrets ----------------------------------------------------------------

module "secrets" {
  source         = "./modules/secrets"
  name           = local.name
  openai_api_key = var.openai_api_key
  tags           = local.tags
}

# ---- Data stores ------------------------------------------------------------

module "database" {
  source                = "./modules/database"
  name                  = local.name
  vpc_id                = module.network.vpc_id
  private_subnet_ids    = module.network.private_subnet_ids
  app_security_group_id = aws_security_group.app.id
  password              = module.secrets.db_password
  instance_class        = var.db_instance_class
  multi_az              = var.db_multi_az
  deletion_protection   = var.db_deletion_protection
  tags                  = local.tags
}

module "cache" {
  source                = "./modules/cache"
  name                  = local.name
  vpc_id                = module.network.vpc_id
  private_subnet_ids    = module.network.private_subnet_ids
  app_security_group_id = aws_security_group.app.id
  node_type             = var.redis_node_type
  replicas              = var.redis_replicas
  tags                  = local.tags
}

module "messaging" {
  source = "./modules/messaging"
  name   = local.name
  tags   = local.tags
}

# ---- Assembled DATABASE_URL secret -----------------------------------------

resource "aws_secretsmanager_secret" "database_url" {
  name = "${local.name}/database-url"
  tags = local.tags
}
resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = format(
    "postgresql+psycopg://aegis:%s@%s:%s/%s",
    module.secrets.db_password,
    module.database.address,
    module.database.port,
    module.database.db_name,
  )
}

# ---- Compute ----------------------------------------------------------------

module "ecs" {
  source = "./modules/ecs"
  name   = local.name
  region = var.region

  vpc_id                = module.network.vpc_id
  private_subnet_ids    = module.network.private_subnet_ids
  app_security_group_id = aws_security_group.app.id
  target_group_arn      = module.alb.target_group_arn

  api_image    = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"
  worker_image = "${aws_ecr_repository.worker.repository_url}:${var.image_tag}"
  perf_image   = "${aws_ecr_repository.perf.repository_url}:${var.image_tag}"
  migrate_image = "${aws_ecr_repository.migrate.repository_url}:${var.image_tag}"

  database_url_secret_arn = aws_secretsmanager_secret.database_url.arn
  jwt_secret_arn          = module.secrets.jwt_secret_arn
  openai_secret_arn       = module.secrets.openai_secret_arn

  redis_url     = module.cache.redis_url
  sqs_queue_url = module.messaging.queue_url
  sqs_queue_arn = module.messaging.queue_arn
  sqs_dlq_arn   = module.messaging.dlq_arn

  llm_provider   = var.llm_provider
  data_provider  = var.data_provider
  sec_user_agent = var.sec_user_agent

  api_desired_count = var.api_desired_count
  worker_min_count  = var.worker_min_count
  worker_max_count  = var.worker_max_count

  tags = local.tags

  # ECS service load_balancer registration requires the listener to exist first.
  depends_on = [module.alb]
}
