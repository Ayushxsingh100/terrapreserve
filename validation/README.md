# validation/

Reserved for dataset validation.

- `smoke/`: a minimal Terraform configuration that checks the pinned Terraform and AWS provider versions work together (`terraform init` and `terraform validate`, no credentials, no `apply`).
- `d1_to_verify/`: evidence for D1 Prompt C, the resolution of the `[TO VERIFY AT D1]` markers in DAIL's specifications. See its `README.md`.
