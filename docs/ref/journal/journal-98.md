# Journal 98

## 2026-06-18 — Complete "Choose a storage service" section in arch-design-planning.md

### Context

The `### Choose a storage service` section in `docs/ref/arch/arch-design-planning.md`
has a stub: a list of partially answered key questions, a brief note on managed
disk types with a screenshot, and a one-liner on data transfer. It lacks the
structured decision tree path and candidates-evaluated table format used in
every other section.

Task: fetch the Microsoft Azure storage technology choice articles and complete
the section using the same format as the other technology choice sections.

### Work log

#### 2026-06-18 — Fetched Azure storage documentation

Fetched three articles linked from the "Choose a storage service" section of the
technology choices overview:

- [Review your storage options](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/storage-options)
- [Azure managed disk types](https://learn.microsoft.com/en-us/azure/virtual-machines/disks-types)
- [Choose a data transfer technology](https://learn.microsoft.com/en-us/azure/architecture/data-guide/scenarios/data-transfer)

Key findings applied to DineSafeViz:

- Of the ten key questions in the storage options article, only two yield a
  "yes" for this project: IaaS disk storage (AKS node OS disks + PostgreSQL
  PVC) and backup/DR (Terraform state → Blob Storage). All others are "no".
- Disk types article confirmed: Standard SSD for OS disk (web/app server tier);
  Standard HDD for the PostgreSQL data disk (non-critical, demo workload).
  Noted: Standard HDD OS disk retirement is September 8, 2028 — not relevant
  since we're using Standard SSD as the OS disk.
- Data transfer: Azure CLI / AzCopy / Azure PowerShell are the correct tier
  for this project. Data Box, Import/Export, and Data Factory are all
  over-engineered for a single-source ETL CronJob.

#### 2026-06-18 — Completed storage service section

Edited `docs/ref/arch/arch-design-planning.md`:

- Replaced the stub "Choose a storage service" section (unanswered key
  questions + one-liner notes) with the full structured format matching other
  technology choice sections.
- Added intro paragraph, decision tree path with all 10 key questions answered,
  "Azure Managed Disk types" subsection, "Azure Blob Storage" subsection,
  "Choose a data transfer technology" subsection, and "Candidates evaluated"
  table with 15 services (4 selected, 11 rejected).
- Updated the Technology Choices Summary to list all selected storage
  components: Standard SSD (OS disk), Standard HDD (PostgreSQL PVC, upgrade
  planned Q1 2028), Azure Blob Storage (Terraform state), and data transfer
  tools.
