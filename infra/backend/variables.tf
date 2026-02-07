variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "tfstate_bucket_name" {
  description = "S3 bucket name for Terraform state"
  type        = string
  default     = "ai-slack-google-connect-tfstate"
}

variable "tfstate_lock_table_name" {
  description = "DynamoDB table name for Terraform state lock"
  type        = string
  default     = "ai-slack-google-connect-tfstate-lock"
}
