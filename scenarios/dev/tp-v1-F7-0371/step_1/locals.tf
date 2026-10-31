locals {
  common_tags = {
    Product       = var.tag_product
    Sub_product   = var.tag_sub_product
    Description   = var.tag_description
    Orchestration = var.tag_orchestration
    Environment   = var.tag_environment
    Contact       = var.tag_contact
    CostCode      = var.tag_constcode
  }
}