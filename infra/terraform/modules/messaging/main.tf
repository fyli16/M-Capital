# Messaging module: research queue + dead-letter queue with redrive.

variable "name" { type = string }
variable "visibility_timeout" {
  type    = number
  default = 300 # > p99 graph latency; workers heartbeat-extend for long LLM calls
}
variable "max_receive_count" {
  type    = number
  default = 5
}
variable "message_retention_seconds" {
  type    = number
  default = 1209600 # 14 days
}
variable "tags" {
  type    = map(string)
  default = {}
}

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name}-research-dlq"
  message_retention_seconds = var.message_retention_seconds
  tags                      = var.tags
}

resource "aws_sqs_queue" "research" {
  name                       = "${var.name}-research"
  visibility_timeout_seconds = var.visibility_timeout
  message_retention_seconds  = var.message_retention_seconds
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })
  tags = var.tags
}

output "queue_url" { value = aws_sqs_queue.research.url }
output "queue_arn" { value = aws_sqs_queue.research.arn }
output "queue_name" { value = aws_sqs_queue.research.name }
output "dlq_url" { value = aws_sqs_queue.dlq.url }
output "dlq_arn" { value = aws_sqs_queue.dlq.arn }
