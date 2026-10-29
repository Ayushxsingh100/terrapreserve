# ==================================================================
# PROVIDER - AWS DEFAULT
# ==================================================================
provider "aws" {
  region = local.aws_region

  default_tags {
    tags = local.aws_default_tags
  }
}
