provider "aws" {
  # Configuration options
  region              = "eu-west-1"
  allowed_account_ids = [var.account_id]
  profile             = var.account_profile
}