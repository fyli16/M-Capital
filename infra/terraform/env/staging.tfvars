environment            = "staging"
region                 = "us-east-1"
single_nat_gateway     = true
db_instance_class      = "db.t4g.medium"
db_multi_az            = false
db_deletion_protection = false
redis_node_type        = "cache.t4g.small"
redis_replicas         = 0
api_desired_count      = 1
worker_min_count       = 1
worker_max_count       = 5
data_provider          = "live"
# openai_api_key / sec_user_agent / image_tag supplied via CI (-var) or TF_VAR_*
