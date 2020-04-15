# Quarantine Chorus Infrastructure

Infrastructure is managed by [terraform][terraform].

## Quickstart

```sh
cd infrastructure

# Write a secrets file
cat > secret.tfvars <<EOF
project = "your-project-id"
credentials_file = "gcp-credentials.json"
EOF

# Output a terraform plan
terraform plan -var-file=secret.tfvars

# Apply changes
terraform apply -var-file=secret.tfvars
```

## Variables

* `credentials_file` -- JSON credentials for a Google Cloud service account
* `project` -- project name
* `bucket_prefix` (optional) prefix for all managed
* `region` (optional)
* `zone` (optional)

[terraform]: https://www.terraform.io/
