output "alb_dns_name" {
  description = "Public endpoint for the API gateway."
  value       = module.alb.alb_dns_name
}
output "ecr_api_url" { value = aws_ecr_repository.api.repository_url }
output "ecr_worker_url" { value = aws_ecr_repository.worker.repository_url }
output "ecr_perf_url" { value = aws_ecr_repository.perf.repository_url }
output "ecr_migrate_url" { value = aws_ecr_repository.migrate.repository_url }
output "ecs_cluster_name" { value = module.ecs.cluster_name }
output "api_service_name" { value = module.ecs.api_service_name }
output "worker_service_name" { value = module.ecs.worker_service_name }
output "migrate_task_family" { value = module.ecs.migrate_task_family }
output "task_subnet_ids" { value = module.ecs.task_subnet_ids }
output "task_security_group_id" { value = module.ecs.task_security_group_id }
output "database_address" {
  value     = module.database.address
  sensitive = true
}
output "sqs_queue_url" { value = module.messaging.queue_url }
