# ============================================================
# ElastiCache Module — Redis Cluster
# ============================================================

variable "cluster_name" { type = string }
variable "node_type" { type = string }
variable "num_replicas" { type = number }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "environment" { type = string }

resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.cluster_name}-redis-subnet"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.cluster_name}-redis-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "Redis access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id = "${var.cluster_name}-redis"
  description          = "CIVA session state Redis cluster"

  node_type            = var.node_type
  num_cache_clusters   = var.num_replicas + 1  # Primary + replicas
  port                 = 6379

  subnet_group_name    = aws_elasticache_subnet_group.this.name
  security_group_ids   = [aws_security_group.redis.id]

  engine               = "redis"
  engine_version       = "7.1"
  parameter_group_name = "default.redis7"

  automatic_failover_enabled = var.num_replicas > 0
  multi_az_enabled          = var.num_replicas > 0
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  snapshot_retention_limit = 7
  snapshot_window         = "03:00-05:00"
  maintenance_window      = "sun:05:00-sun:07:00"

  tags = {
    Environment = var.environment
  }
}

output "primary_endpoint" {
  value = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "reader_endpoint" {
  value = aws_elasticache_replication_group.this.reader_endpoint_address
}
