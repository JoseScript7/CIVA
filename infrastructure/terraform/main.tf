# ============================================================
# CIVA Platform — Terraform Root Module
# ============================================================
# Provisions the complete AWS infrastructure:
#   - EKS cluster (Kubernetes)
#   - MSK cluster (Kafka)
#   - ElastiCache (Redis)
#   - RDS/TimescaleDB
#   - S3 buckets
#   - SageMaker endpoints
# ============================================================

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }

  backend "s3" {
    bucket         = "civa-terraform-state"
    key            = "civa/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "civa-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "CIVA"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ---- Networking ----
data "aws_availability_zones" "available" {
  state = "available"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.5.0"

  name = "civa-${var.environment}-vpc"
  cidr = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "prod"
  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

# ---- EKS Cluster ----
module "eks" {
  source = "./modules/eks"

  cluster_name    = "civa-${var.environment}"
  cluster_version = "1.29"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
  environment     = var.environment

  node_groups = {
    edge = {
      instance_types = ["c6i.xlarge"]
      min_size       = 2
      max_size       = 10
      desired_size   = 3
      labels = {
        "workload-type" = "edge"
      }
    }
    ml = {
      instance_types = ["m6i.2xlarge"]
      min_size       = 2
      max_size       = 8
      desired_size   = 2
      labels = {
        "workload-type" = "ml"
      }
    }
    general = {
      instance_types = ["m6i.xlarge"]
      min_size       = 2
      max_size       = 6
      desired_size   = 3
      labels = {
        "workload-type" = "general"
      }
    }
  }
}

# ---- MSK (Kafka) ----
module "msk" {
  source = "./modules/msk"

  cluster_name   = "civa-${var.environment}"
  kafka_version  = "3.6.0"
  broker_count   = var.environment == "prod" ? 6 : 3
  instance_type  = var.environment == "prod" ? "kafka.m5.2xlarge" : "kafka.m5.large"
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_subnets
  ebs_volume_gb  = var.environment == "prod" ? 1000 : 100
  environment    = var.environment
}

# ---- ElastiCache (Redis) ----
module "elasticache" {
  source = "./modules/elasticache"

  cluster_name  = "civa-${var.environment}"
  node_type     = var.environment == "prod" ? "cache.r6g.xlarge" : "cache.r6g.large"
  num_replicas  = var.environment == "prod" ? 2 : 1
  vpc_id        = module.vpc.vpc_id
  subnet_ids    = module.vpc.private_subnets
  environment   = var.environment
}

# ---- RDS (TimescaleDB) ----
module "rds" {
  source = "./modules/rds"

  identifier     = "civa-${var.environment}-timescaledb"
  engine_version = "16"
  instance_class = var.environment == "prod" ? "db.r6g.2xlarge" : "db.r6g.large"
  storage_gb     = var.environment == "prod" ? 500 : 100
  db_name        = "civa_behavior"
  db_username    = "civa"
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_subnets
  environment    = var.environment
}

# ---- S3 Buckets ----
module "s3" {
  source = "./modules/s3"

  environment = var.environment
  buckets = {
    forensics = {
      name       = "civa-${var.environment}-forensics"
      versioning = true
      lifecycle_days = 365
    }
    models = {
      name       = "civa-${var.environment}-models"
      versioning = true
      lifecycle_days = 0  # Keep forever
    }
    terraform_state = {
      name       = "civa-terraform-state"
      versioning = true
      lifecycle_days = 0
    }
  }
}

# ---- SageMaker ----
module "sagemaker" {
  source = "./modules/sagemaker"

  project_name     = "civa-${var.environment}"
  model_bucket     = module.s3.bucket_arns["models"]
  instance_type    = var.environment == "prod" ? "ml.m5.xlarge" : "ml.m5.large"
  instance_count   = var.environment == "prod" ? 2 : 1
  vpc_id           = module.vpc.vpc_id
  subnet_ids       = module.vpc.private_subnets
  environment      = var.environment
}
