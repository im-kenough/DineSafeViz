# Bootstrap a landing zone

This guide creates an environment's landing zone with Terraform: its state
account, CI identities, operator account and group, role assignments, and
locks. You run it once per environment, as `dsv-admin01`, from your
workstation. CI never applies the landing zone.

The first apply can't store its state in the account it's creating, so it
uses a local state file. `make migrate` then moves that state into the new
account. For the identities and roles it creates, see
[Identity and access management](../../../docs/ref/iam.md).

## Before you begin

You need the following:

- Terraform 1.16, tflint, `jq`, and the Azure CLI.
- `az login` as `dsv-admin01`.
- The operator account `dsv-ops-<env>01`, created in the Entra admin center
  with the alias (mail nickname) `dsv-ops-<env>01`, and signed in to once to
  enroll MFA.
- `infra/terraform/envs/<env>/landing-zone.secret.tfvars`, copied from the
  `.example` file next to it, with the budget's contact address.

## Plan the first apply

This step writes a local backend override and import blocks for the
resources that already exist, then saves a plan. It changes nothing in
Azure.

1.  Select the environment's subscription. The Makefile stops if `az` is on
    a different one.

    ```bash
    cd infra
    az account set --subscription <subscription-id>
    ```

2.  Run the bootstrap:

    ```bash
    make bootstrap ENV=stg
    ```

3.  Read the summary at the end. It must import the operator group, the
    budget, and each operator role assignment that already exists, update
    only the group's description, and delete or replace nothing.

## Apply and migrate

This step creates the landing zone, then moves its state to Azure.

1.  Apply the saved plan:

    ```bash
    make apply ENV=stg LAYER=landing-zone
    ```

2.  Migrate the state:

    ```bash
    make migrate ENV=stg
    ```

    If it fails with `403` or `AuthorizationPermissionMismatch`, your new
    Storage Blob Data Contributor role isn't active yet. Wait five minutes
    and run it again.

3.  Check the plan that `make migrate` prints at the end. It must report
    `0 to import, 0 to add, 0 to change`.
4.  Delete the local state files:

    ```bash
    rm terraform/envs/stg/landing-zone.bootstrap.tfstate*
    ```

## Change the landing zone later

After the bootstrap, you change the landing zone with the same two targets
that every layer uses:

```bash
make plan ENV=stg LAYER=landing-zone
make apply ENV=stg LAYER=landing-zone
```

The `CanNotDelete` lock on `rg-dsv-<env>01-iac` blocks deleting anything in
that group, including federated credentials. To delete something there,
set `lock_iac_rg = false` in `envs/<env>/landing-zone.tfvars`, plan and
apply, make your change, then set it back to `true` and apply again.

## Next steps

- [Identity and access management](../../../docs/ref/iam.md) lists every
  identity and role this creates.
- [Azure resources](../../ref/6-azure-resources.md) lists the resources by
  layer.
