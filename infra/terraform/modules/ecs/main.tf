# ECS module: Fargate cluster running api-gateway (behind ALB), agent-worker
# (autoscaled on SQS depth), and a scheduled performance-worker task.

variable "name" { type = string }
variable "region" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "app_security_group_id" { type = string }
variable "target_group_arn" { type = string }

variable "api_image" { type = string }
variable "worker_image" { type = string }
variable "perf_image" { type = string }
variable "migrate_image" { type = string }

variable "container_port" {
  type    = number
  default = 8000
}

# Secret ARNs (injected as container secrets)
variable "database_url_secret_arn" { type = string }
variable "jwt_secret_arn" { type = string }
variable "openai_secret_arn" { type = string }

# Plain env
variable "redis_url" { type = string }
variable "sqs_queue_url" { type = string }
variable "sqs_queue_arn" { type = string }
variable "sqs_dlq_arn" { type = string }
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

# Sizing
variable "api_cpu" { default = 512 }
variable "api_memory" { default = 1024 }
variable "api_desired_count" { default = 2 }
variable "worker_cpu" { default = 1024 }
variable "worker_memory" { default = 2048 }
variable "worker_min_count" { default = 1 }
variable "worker_max_count" { default = 10 }
variable "worker_backlog_target" {
  type    = number
  default = 20 # target visible messages; see autoscaling note below
}
variable "perf_cpu" { default = 512 }
variable "perf_memory" { default = 1024 }
variable "perf_schedule" {
  type    = string
  default = "rate(1 hour)"
}
variable "log_retention_days" {
  type    = number
  default = 30
}
variable "tags" {
  type    = map(string)
  default = {}
}

locals {
  common_env = [
    { name = "AWS_REGION", value = var.region },
    { name = "REDIS_URL", value = var.redis_url },
    { name = "SQS_RESEARCH_QUEUE_URL", value = var.sqs_queue_url },
    { name = "LLM_PROVIDER", value = var.llm_provider },
    { name = "DATA_PROVIDER", value = var.data_provider },
    { name = "SEC_USER_AGENT", value = var.sec_user_agent },
  ]
  common_secrets = [
    { name = "DATABASE_URL", valueFrom = var.database_url_secret_arn },
    { name = "OPENAI_API_KEY", valueFrom = var.openai_secret_arn },
  ]
}

# ---- Cluster + logs ---------------------------------------------------------

resource "aws_ecs_cluster" "this" {
  name = "${var.name}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = var.tags
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.name}/api-gateway"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}
resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${var.name}/agent-worker"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}
resource "aws_cloudwatch_log_group" "perf" {
  name              = "/ecs/${var.name}/performance-worker"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}
resource "aws_cloudwatch_log_group" "migrate" {
  name              = "/ecs/${var.name}/migrate"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# ---- IAM --------------------------------------------------------------------

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${var.name}-ecs-exec"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "exec_secrets" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.database_url_secret_arn, var.jwt_secret_arn, var.openai_secret_arn]
  }
}
resource "aws_iam_role_policy" "exec_secrets" {
  name   = "secrets-read"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.exec_secrets.json
}

resource "aws_iam_role" "task" {
  name               = "${var.name}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = var.tags
}

data "aws_iam_policy_document" "task_perms" {
  statement {
    sid = "Sqs"
    actions = [
      "sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage",
      "sqs:GetQueueAttributes", "sqs:ChangeMessageVisibility",
    ]
    resources = [var.sqs_queue_arn, var.sqs_dlq_arn]
  }
  statement {
    sid       = "Secrets"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.database_url_secret_arn, var.jwt_secret_arn, var.openai_secret_arn]
  }
}
resource "aws_iam_role_policy" "task_perms" {
  name   = "task-perms"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task_perms.json
}

# ---- Task definitions -------------------------------------------------------

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = var.api_image
    essential = true
    portMappings = [{ containerPort = var.container_port, protocol = "tcp" }]
    environment = local.common_env
    secrets = concat(local.common_secrets, [
      { name = "JWT_SECRET", valueFrom = var.jwt_secret_arn },
    ])
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "api"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request;urllib.request.urlopen('http://localhost:${var.container_port}/health')\" || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 20
    }
  }])
  tags = var.tags
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name        = "worker"
    image       = var.worker_image
    essential   = true
    command     = ["python", "-m", "app", "consume"]
    environment = local.common_env
    secrets     = local.common_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.worker.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "worker"
      }
    }
  }])
  tags = var.tags
}

resource "aws_ecs_task_definition" "perf" {
  family                   = "${var.name}-perf"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.perf_cpu
  memory                   = var.perf_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name        = "perf"
    image       = var.perf_image
    essential   = true
    command     = ["python", "-m", "app", "run"]
    environment = local.common_env
    secrets     = local.common_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.perf.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "perf"
      }
    }
  }])
  tags = var.tags
}

resource "aws_ecs_task_definition" "migrate" {
  family                   = "${var.name}-migrate"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "migrate"
    image     = var.migrate_image
    essential = true
    # Image CMD runs `alembic upgrade head`; only DATABASE_URL is needed.
    secrets = [{ name = "DATABASE_URL", valueFrom = var.database_url_secret_arn }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.migrate.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "migrate"
      }
    }
  }])
  tags = var.tags
}

# ---- Services ---------------------------------------------------------------
resource "aws_ecs_service" "api" {
  name            = "${var.name}-api"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.app_security_group_id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "api"
    container_port   = var.container_port
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  tags = var.tags
}

resource "aws_ecs_service" "worker" {
  name            = "${var.name}-worker"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_min_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.app_security_group_id]
    assign_public_ip = false
  }
  tags = var.tags
}

# ---- Autoscaling ------------------------------------------------------------

# API: CPU target tracking.
resource "aws_appautoscaling_target" "api" {
  max_capacity       = 10
  min_capacity       = var.api_desired_count
  resource_id        = "service/${aws_ecs_cluster.this.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}
resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "${var.name}-api-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 60
  }
}

# Worker: scale on SQS backlog. NOTE: this tracks absolute visible-message count;
# a backlog-per-task refinement (messages / runningTasks via metric math) is the
# production-grade upgrade.
resource "aws_appautoscaling_target" "worker" {
  max_capacity       = var.worker_max_count
  min_capacity       = var.worker_min_count
  resource_id        = "service/${aws_ecs_cluster.this.name}/${aws_ecs_service.worker.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}
resource "aws_appautoscaling_policy" "worker_sqs" {
  name               = "${var.name}-worker-sqs"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker.resource_id
  scalable_dimension = aws_appautoscaling_target.worker.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker.service_namespace
  target_tracking_scaling_policy_configuration {
    customized_metric_specification {
      metric_name = "ApproximateNumberOfMessagesVisible"
      namespace   = "AWS/SQS"
      statistic   = "Average"
      dimensions {
        name  = "QueueName"
        value = element(split("/", var.sqs_queue_url), length(split("/", var.sqs_queue_url)) - 1)
      }
    }
    target_value       = var.worker_backlog_target
    scale_in_cooldown  = 120
    scale_out_cooldown = 30
  }
}

# ---- Scheduled performance-worker task -------------------------------------

resource "aws_iam_role" "events" {
  name = "${var.name}-events"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}
resource "aws_iam_role_policy" "events" {
  name = "run-perf-task"
  role = aws_iam_role.events.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["ecs:RunTask"], Resource = aws_ecs_task_definition.perf.arn },
      { Effect = "Allow", Action = ["iam:PassRole"], Resource = [aws_iam_role.execution.arn, aws_iam_role.task.arn] },
    ]
  })
}

resource "aws_cloudwatch_event_rule" "perf" {
  name                = "${var.name}-perf-schedule"
  schedule_expression = var.perf_schedule
  tags                = var.tags
}
resource "aws_cloudwatch_event_target" "perf" {
  rule     = aws_cloudwatch_event_rule.perf.name
  arn      = aws_ecs_cluster.this.arn
  role_arn = aws_iam_role.events.arn
  ecs_target {
    task_definition_arn = aws_ecs_task_definition.perf.arn
    task_count          = 1
    launch_type         = "FARGATE"
    network_configuration {
      subnets          = var.private_subnet_ids
      security_groups  = [var.app_security_group_id]
      assign_public_ip = false
    }
  }
}

output "cluster_name" { value = aws_ecs_cluster.this.name }
output "api_service_name" { value = aws_ecs_service.api.name }
output "worker_service_name" { value = aws_ecs_service.worker.name }
output "migrate_task_family" { value = aws_ecs_task_definition.migrate.family }
output "task_subnet_ids" { value = var.private_subnet_ids }
output "task_security_group_id" { value = var.app_security_group_id }
