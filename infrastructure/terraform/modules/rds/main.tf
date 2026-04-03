# ============================================================
# RDS Module — TimescaleDB (PostgreSQL)
# ============================================================

variable "identifier" { type = string }
variable "engine_version" { type = string }
variable "instance_class" { type = string }
variable "storage_gb" { type = number }
variable "db_name" { type = string }
variable "db_username" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "environment" { type = string }

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.identifier}-subnet"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.identifier}-rds-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "PostgreSQL access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "this" {
  identifier = var.identifier

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage     = var.storage_gb
  max_allocated_storage = var.storage_gb * 2
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az            = var.environment == "prod"
  publicly_accessible = false

  backup_retention_period = 7
  backup_window          = "02:00-04:00"
  maintenance_window     = "sun:04:00-sun:06:00"

  deletion_protection = var.environment == "prod"
  skip_final_snapshot = var.environment != "prod"

  performance_insights_enabled = true

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "civa/${var.environment}/timescaledb-password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db.result
}

output "endpoint" {
  value = aws_db_instance.this.endpoint
}

output "db_name" {
  value = aws_db_instance.this.db_name
}
