provider "google" {
  credentials = "${file("/Users/ravi/Terraform/account.json")}"
  project = "ansible-gce-244616"
  region = "asia-south1-a"
}

provider "aws" {
  region = "us-east-2"
}
