environment            = "prod"
region                 = "us-east-1"
single_nat_gateway     = false
db_instance_class      = "db.r6g.large"
db_multi_az            = true
db_deletion_protection = true
redis_node_type        = "cache.r6g.large"
redis_replicas         = 1
api_desired_count      = 3
worker_min_count       = 2
worker_max_count       = 20
data_provider          = "live"
# certificate_arn = "arn:aws:acm:...:certificate/..."  # enable HTTPS
# openai_api_key / sec_user_agent / image_tag supplied via CI (-var) or TF_VAR_*
