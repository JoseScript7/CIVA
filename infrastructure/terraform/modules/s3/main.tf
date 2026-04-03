# ============================================================
# S3 Module — Object Storage
# ============================================================

variable "environment" { type = string }
variable "buckets" {
  type = map(object({
    name           = string
    versioning     = bool
    lifecycle_days = number
  }))
}

resource "aws_s3_bucket" "this" {
  for_each = var.buckets

  bucket = each.value.name

  tags = {
    Environment = var.environment
    Purpose     = each.key
  }
}

resource "aws_s3_bucket_versioning" "this" {
  for_each = { for k, v in var.buckets : k => v if v.versioning }

  bucket = aws_s3_bucket.this[each.key].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  for_each = { for k, v in var.buckets : k => v if v.lifecycle_days > 0 }

  bucket = aws_s3_bucket.this[each.key].id

  rule {
    id     = "archive-old-data"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = each.value.lifecycle_days
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = var.buckets

  bucket = aws_s3_bucket.this[each.key].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  for_each = var.buckets

  bucket = aws_s3_bucket.this[each.key].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_arns" {
  value = { for k, v in aws_s3_bucket.this : k => v.arn }
}

output "bucket_names" {
  value = { for k, v in aws_s3_bucket.this : k => v.bucket }
}
