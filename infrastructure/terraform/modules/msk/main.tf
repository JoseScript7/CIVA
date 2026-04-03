# ============================================================
# MSK Module — Kafka Cluster
# ============================================================

variable "cluster_name" { type = string }
variable "kafka_version" { type = string }
variable "broker_count" { type = number }
variable "instance_type" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "ebs_volume_gb" { type = number }
variable "environment" { type = string }

resource "aws_security_group" "msk" {
  name_prefix = "${var.cluster_name}-msk-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 9092
    to_port     = 9098
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "Kafka broker ports"
  }

  ingress {
    from_port   = 2181
    to_port     = 2181
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "ZooKeeper"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.cluster_name}-msk"
    Environment = var.environment
  }
}

resource "aws_msk_cluster" "this" {
  cluster_name           = var.cluster_name
  kafka_version          = var.kafka_version
  number_of_broker_nodes = var.broker_count

  broker_node_group_info {
    instance_type = var.instance_type
    storage_info {
      ebs_storage_info {
        volume_size = var.ebs_volume_gb
      }
    }
    client_subnets  = var.subnet_ids
    security_groups = [aws_security_group.msk.id]
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS_PLAINTEXT"
      in_cluster    = true
    }
  }

  configuration_info {
    arn      = aws_msk_configuration.this.arn
    revision = aws_msk_configuration.this.latest_revision
  }

  open_monitoring {
    prometheus {
      jmx_exporter {
        enabled_in_broker = true
      }
      node_exporter {
        enabled_in_broker = true
      }
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk.name
      }
    }
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_msk_configuration" "this" {
  name              = "${var.cluster_name}-config"
  kafka_versions    = [var.kafka_version]

  server_properties = <<PROPERTIES
auto.create.topics.enable=false
default.replication.factor=3
min.insync.replicas=2
num.partitions=12
log.retention.hours=168
log.segment.bytes=1073741824
compression.type=lz4
PROPERTIES
}

resource "aws_cloudwatch_log_group" "msk" {
  name              = "/aws/msk/${var.cluster_name}"
  retention_in_days = 30
}

output "bootstrap_brokers" {
  value = aws_msk_cluster.this.bootstrap_brokers_tls
}

output "zookeeper_connect" {
  value = aws_msk_cluster.this.zookeeper_connect_string
}
