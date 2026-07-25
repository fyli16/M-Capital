#!/bin/bash
# Provision the SQS queues LocalStack serves for the e2e stack.
set -euo pipefail
awslocal sqs create-queue --queue-name aegis-research-dlq
awslocal sqs create-queue \
  --queue-name aegis-research \
  --attributes '{"VisibilityTimeout":"120"}'
echo "e2e SQS queues created"
