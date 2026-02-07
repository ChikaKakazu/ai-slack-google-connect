terraform {
  backend "s3" {
    bucket         = "ai-slack-google-connect-tfstate"
    key            = "aws/terraform.tfstate"
    region         = "ap-northeast-1"
    dynamodb_table = "ai-slack-google-connect-tfstate-lock"
    encrypt        = true
  }
}
