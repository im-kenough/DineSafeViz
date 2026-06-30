# 2026-06-22 17:10
- Read user request to explain the Baseline architecture for an Azure Kubernetes Service (AKS) cluster from https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks/baseline-aks, enumerate components, and estimate the monthly deployment cost.
- Created this journal file.
- Fetching the URL content to extract the architectural explanation and component list.
- Extracted the components and architecture explanation from the Microsoft documentation.
- Noted that the exact pricing depends on deployment configuration. The baseline production configuration starts at around $300-$500/month, as estimated by standard Azure pricing calculations and web research.

# 2026-06-22 17:27
- User asked for a Mermaid diagram of Microsoft's AKS baseline architecture, drawn into `docs/ref/arch/design-planning/arch-design-aks.md`, because the official SVG (`aks-baseline-architecture.svg`) may not capture everything.
- Re-fetched the baseline doc with a prompt enumerating every component and flow (hub-spoke VNets/subnets, App Gateway + WAF, system/user node pools, Traefik ingress, internal LB, ACR/Key Vault private endpoints, API server subnet, Azure Firewall egress + UDR, Bastion + jump box, gateway, Azure Monitor/Log Analytics/Container Insights, Defender, Entra ID, workload identity, private DNS zones).
- Added a new `### AKS Baseline reference architecture` subsection under `## Reference architectures implemented`, before the existing `### Modified AKS Baseline Architecture`. Placed there so the canonical reference precedes the DineSafeViz cost-optimized adaptation and the conformance table.
- Diagram is a `flowchart TB` with three edge styles as a legend: thick (`==>`) inbound data path, solid (`-->`) egress + Private Link, dotted (`-.->`) control plane (identity, observability, DNS, on-prem). Modeled the UDR -> firewall hop as its own hexagon node and showed Private Link traffic to ACR/Key Vault bypassing the firewall — the two things the layered SVG understates.
- Verified rendering: extracted the fenced block and ran `npx -y -p @mermaid-js/mermaid-cli mmdc -i dsv-aks.mmd -o dsv-aks.svg`. Result: `Generating single mermaid chart`, EXIT=0, 199 KB SVG produced. Syntax is valid.
- This diagram intentionally depicts the stock Microsoft baseline, not the DSV deployment (single VNet, public API, NGINX + Standard LB, AKS-managed egress, public ACR/Key Vault endpoints). Those divergences remain documented in the conformance table that follows.

# 2026-06-22 17:40
- Received request to explain how Azure Bastion normally works for the baseline AKS mode and check if there is a free tier.
- Researching Azure Bastion Developer SKU and pricing.

# 2026-06-22 17:44
- Received request to draw a diagram showing all scenarios for using Azure Bastion to run kubectl commands.
- Generating a markdown artifact containing a Mermaid diagram illustrating the two primary methods (Direct Tunneling via Standard SKU vs. Jump-box via Developer SKU).

# 2026-06-22 17:46
- User requested to move the Azure Bastion scenarios diagram artifact to the docs directory.
- Copied the artifact into `docs/ref/arch/design-planning/bastion-kubectl-scenarios.md`.

# 2026-06-22 17:52
- User asked to confirm the workflow for Scenario B and whether installing the Azure CLI would allow SSHing into the jumpbox directly from a local Linux terminal instead of the browser.
- Confirmed that the "Native Client" feature (which enables `az network bastion ssh`) is strictly limited to the Standard or Premium SKUs. It cannot be used with the Developer (free) SKU.

# 2026-06-22 17:59
- User asked how virtual network peering works, if it's a paid feature, and if a Bastion VM in a hub network can communicate with a spoke network without peering.
- Verified that peering securely routes traffic over the Microsoft backbone for a nominal data transfer fee. Also verified that connecting hub and spoke without peering requires a VPN/vWAN, and critically, the free Bastion Developer SKU does *not* support VNet peering at all.

# 2026-06-22 18:04
- User asked for an explanation of how the "public endpoint subnet" works.
- Clarifying the terminology, as there is no single "public endpoint subnet" in the baseline architecture, but rather subnets that host public-facing resources (App Gateway, Bastion) versus Private Endpoint subnets.
