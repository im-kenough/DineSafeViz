# infra/Makefile
#
# Orchestrates all IaC operations for DineSafeViz.
# Run targets from the infra/ directory: cd infra && make <target>
#
# Prerequisites: Packer, Terraform, Ansible, Python 3 with PyYAML
# Secrets: stored in ansible/vault/secrets.yml (Ansible Vault encrypted)

SHELL := /bin/bash
.DEFAULT_GOAL := help

ANSIBLE_DIR := ansible
TERRAFORM_DIR := terraform
PACKER_DIR := packer
VAULT_FILE := $(ANSIBLE_DIR)/vault/secrets.yml

# --- Image Pipeline ---

.PHONY: bake-base
bake-base: ## Build ubuntu-base template (Layer 1)
	cd $(PACKER_DIR) && \
	ansible-vault view ../$(VAULT_FILE) --ask-vault-pass \
		| python3 ../scripts/render-pkrvars.py > variables.pkrvars.hcl && \
	packer init ubuntu-base.pkr.hcl && \
	packer build -var-file=variables.pkrvars.hcl ubuntu-base.pkr.hcl; \
	rm -f variables.pkrvars.hcl

.PHONY: bake-docker
bake-docker: ## Build ubuntu-docker template (Layer 2, requires Layer 1)
	cd $(PACKER_DIR) && \
	ansible-vault view ../$(VAULT_FILE) --ask-vault-pass \
		| python3 ../scripts/render-pkrvars.py > variables.pkrvars.hcl && \
	packer init ubuntu-docker.pkr.hcl && \
	packer build -var-file=variables.pkrvars.hcl ubuntu-docker.pkr.hcl; \
	rm -f variables.pkrvars.hcl

.PHONY: bake-dsv-app
bake-dsv-app: ## Build dsv-app template (Layer 3, requires Layer 2)
	cd $(PACKER_DIR) && \
	ansible-vault view ../$(VAULT_FILE) --ask-vault-pass \
		| python3 ../scripts/render-pkrvars.py > variables.pkrvars.hcl && \
	packer init dsv-app.pkr.hcl && \
	packer build -var-file=variables.pkrvars.hcl dsv-app.pkr.hcl; \
	rm -f variables.pkrvars.hcl

.PHONY: bake-all
bake-all: bake-base bake-docker bake-dsv-app ## Build all image layers in order

# --- VM Provisioning ---

.PHONY: provision-vm
provision-vm: ## Provision VM from dsv-app template via Terraform
	ansible-vault view $(VAULT_FILE) --ask-vault-pass \
		| python3 scripts/render-tfvars.py > $(TERRAFORM_DIR)/terraform.tfvars
	cd $(TERRAFORM_DIR) && terraform init && terraform apply
	@rm -f $(TERRAFORM_DIR)/terraform.tfvars

.PHONY: destroy-vm
destroy-vm: ## Destroy the VM via Terraform
	ansible-vault view $(VAULT_FILE) --ask-vault-pass \
		| python3 scripts/render-tfvars.py > $(TERRAFORM_DIR)/terraform.tfvars
	cd $(TERRAFORM_DIR) && terraform destroy
	@rm -f $(TERRAFORM_DIR)/terraform.tfvars

# --- App Deployment ---

.PHONY: deploy-app
deploy-app: ## Deploy app: clone repo, template .env, docker compose up
	cd $(ANSIBLE_DIR) && ansible-playbook playbooks/deploy-dsv.yml --ask-vault-pass

.PHONY: destroy-app
destroy-app: ## Destroy app: docker compose down -v, remove repo (full wipe)
	cd $(ANSIBLE_DIR) && ansible-playbook playbooks/destroy-dsv.yml --ask-vault-pass

.PHONY: destroy-app-keep-data
destroy-app-keep-data: ## Destroy app but keep Docker volumes
	cd $(ANSIBLE_DIR) && ansible-playbook playbooks/destroy-dsv.yml --ask-vault-pass -e "keep_data=true"

.PHONY: redeploy-app
redeploy-app: destroy-app deploy-app ## Full wipe and redeploy

.PHONY: redeploy-app-keep-data
redeploy-app-keep-data: destroy-app-keep-data deploy-app ## Redeploy, keeping Docker volumes

# --- Convenience ---

.PHONY: up
up: provision-vm deploy-app ## Full stack: provision VM + deploy app

.PHONY: down
down: destroy-app destroy-vm ## Tear down everything: destroy app + destroy VM

# --- Help ---

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-28s\033[0m %s\n", $$1, $$2}'
