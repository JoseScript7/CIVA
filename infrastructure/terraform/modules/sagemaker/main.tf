# ============================================================
# SageMaker Module — ML Model Serving
# ============================================================

variable "project_name" { type = string }
variable "model_bucket" { type = string }
variable "instance_type" { type = string }
variable "instance_count" { type = number }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "environment" { type = string }

resource "aws_iam_role" "sagemaker" {
  name = "${var.project_name}-sagemaker-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "sagemaker.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "sagemaker_full" {
  role       = aws_iam_role.sagemaker.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy" "s3_access" {
  name = "${var.project_name}-s3-access"
  role = aws_iam_role.sagemaker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ]
      Resource = [
        var.model_bucket,
        "${var.model_bucket}/*"
      ]
    }]
  })
}

resource "aws_security_group" "sagemaker" {
  name_prefix = "${var.project_name}-sagemaker-"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = var.environment
  }
}

# SageMaker endpoint configuration
# Model and endpoint are created via the training pipeline, not Terraform
# This provides the IAM roles and networking for the endpoint

output "execution_role_arn" {
  value = aws_iam_role.sagemaker.arn
}

output "security_group_id" {
  value = aws_security_group.sagemaker.id
}

output "endpoint_name" {
  value = "${var.project_name}-behavior-model"
}
