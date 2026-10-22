# Entry point for infrastructure work. CI jobs sign in and call these
# targets; your workstation runs the same targets as the fallback.
# Run `make help` for the list. Design:
# docs/superpowers/specs/2026-10-19-iac-cicd-design.md
#
# Every target that touches Azure first checks that `az` is signed in to the
# subscription in terraform/envs/$(ENV)/env.tfvars.

SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory

ENV ?=
LAYER ?=

# Paths after -chdir are relative to the layer directory.
TF = terraform -chdir=terraform/$(LAYER)
ENV_DIR = ../envs/$(ENV)
PLAN = $(ENV).tfplan
SECRET_VARS = terraform/envs/$(ENV)/$(LAYER).secret.tfvars
VAR_FILES = -var-file=$(ENV_DIR)/env.tfvars -var-file=$(ENV_DIR)/$(LAYER).tfvars \
	$(if $(wildcard $(SECRET_VARS)),-var-file=$(ENV_DIR)/$(LAYER).secret.tfvars)
# During a landing zone bootstrap, backend_override.tf selects local state.
BACKEND_ARGS = $(if $(wildcard terraform/$(LAYER)/backend_override.tf),,-backend-config=$(ENV_DIR)/$(LAYER).backend.hcl)
LAYERS = $(notdir $(wildcard terraform/landing-zone terraform/core terraform/compute))
TFLINT_CONFIG = $(CURDIR)/terraform/.tflint.hcl
# Allowlist checks done by make, so a bad ENV or LAYER never reaches a shell
# string: each is empty unless the value is one word from the list.
ENV_OK = $(and $(filter 1,$(words $(ENV))),$(filter $(ENV),stg prod))
LAYER_OK = $(and $(filter 1,$(words $(LAYER))),$(filter $(LAYER),$(LAYERS)))
PLAN_FILES = terraform/$(LAYER)/$(PLAN) terraform/$(LAYER)/$(PLAN).json

.PHONY: help check-env check-layer init plan apply bootstrap migrate lint test

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

check-env:
	@if [[ -z "$(ENV_OK)" ]]; then echo "ERROR: set ENV=stg or ENV=prod" >&2; exit 2; fi
	@want=$$(sed -n 's/^subscription_id *= *"\(.*\)"/\1/p' terraform/envs/$(ENV)/env.tfvars); \
	have=$$(az account show --query id -o tsv); \
	if [[ "$$have" != "$$want" ]]; then \
	  echo "ERROR: az is on subscription $$have, but ENV=$(ENV) needs $$want." >&2; \
	  echo "Run: az account set --subscription $$want" >&2; exit 1; fi

check-layer:
	@if [[ -z "$(LAYER_OK)" ]]; then echo "ERROR: set LAYER to one of: $(LAYERS)" >&2; exit 2; fi
	@if [[ -f $(SECRET_VARS).example && ! -f $(SECRET_VARS) ]]; then \
	  echo "ERROR: copy $(SECRET_VARS).example to $(SECRET_VARS) and fill it in." >&2; exit 2; fi

init: check-env check-layer ## terraform init for ENV and LAYER
	$(TF) init -input=false -reconfigure $(BACKEND_ARGS)

# A refused plan is deleted, so make apply can't pick it up.
plan: init ## Save a plan for ENV and LAYER, and summarize it
	$(TF) plan -input=false $(VAR_FILES) -out=$(PLAN)
	$(TF) show -json $(PLAN) > terraform/$(LAYER)/$(PLAN).json
	terraform/plan-summary.sh terraform/$(LAYER)/$(PLAN).json || { rm -f $(PLAN_FILES); exit 1; }

# apply summarizes the saved plan again, in case it is stale or was put there
# by hand, so the destroy guard holds unless ALLOW_DESTROY=1.
apply: init ## Apply the plan saved by make plan
	@if [[ ! -f terraform/$(LAYER)/$(PLAN) ]]; then \
	  echo "ERROR: no saved plan. Run: make plan ENV=$(ENV) LAYER=$(LAYER)" >&2; exit 1; fi
	$(TF) show -json $(PLAN) > terraform/$(LAYER)/$(PLAN).json
	terraform/plan-summary.sh terraform/$(LAYER)/$(PLAN).json || { rm -f $(PLAN_FILES); exit 1; }
	$(TF) apply -input=false $(PLAN)
	rm -f $(PLAN_FILES)

lint: ## fmt, validate, tflint, and shellcheck
	terraform fmt -check -recursive terraform
	@for d in $(LAYERS); do \
	  terraform -chdir=terraform/$$d init -input=false -backend=false > /dev/null; \
	  terraform -chdir=terraform/$$d validate; done
	tflint --init --config=$(TFLINT_CONFIG) > /dev/null
	@for d in $(LAYERS); do tflint --chdir=terraform/$$d --config=$(TFLINT_CONFIG); done
	shellcheck terraform/*.sh terraform/*/*.sh terraform/tests/*.sh

test: ## Run the tooling's own tests
	terraform/tests/test-plan-summary.sh
