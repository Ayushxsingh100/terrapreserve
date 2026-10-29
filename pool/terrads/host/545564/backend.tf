terraform {
  backend "s3" {
    bucket = "your-bucket"
    key    = "location/terraform.tfstate"
    region = "sa-east-1"
  }
}