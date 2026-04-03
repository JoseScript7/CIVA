# ============================================================
# CIVA Platform — Terraform Outputs
# ============================================================

output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "msk_bootstrap_brokers" {
  description = "MSK bootstrap broker connection string"
  value       = module.msk.bootstrap_brokers
}

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = module.elasticache.primary_endpoint
  sensitive   = true
}

output "timescaledb_endpoint" {
  description = "RDS TimescaleDB endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "s3_forensics_bucket" {
  description = "S3 bucket for forensic logs"
  value       = module.s3.bucket_names["forensics"]
}

output "s3_models_bucket" {
  description = "S3 bucket for ML model artifacts"
  value       = module.s3.bucket_names["models"]
}

output "sagemaker_endpoint" {
  description = "SageMaker inference endpoint name"
  value       = module.sagemaker.endpoint_name
}
