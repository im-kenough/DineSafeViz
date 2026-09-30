# Azure Bastion Scenarios for AKS `kubectl` Access

This document details the two primary methods for securely executing `kubectl` commands against a private Azure Kubernetes Service (AKS) cluster using Azure Bastion.

```mermaid
flowchart TD
    %% Define the styles for different components
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef bastion fill:#0072C6,stroke:#fff,stroke-width:2px,color:#fff;
    classDef cluster fill:#326CE5,stroke:#fff,stroke-width:2px,color:#fff;
    classDef jumpbox fill:#5C2D91,stroke:#fff,stroke-width:2px,color:#fff;
    classDef internet fill:#e0e0e0,stroke:#666,stroke-width:1px,stroke-dasharray: 5 5;

    %% Scenario A
    subgraph ScenarioA ["Scenario A: Direct API Server Tunneling (Requires Standard/Premium SKU)"]
        direction LR
        Local1["Local Machine / Developer Laptop<br><i>(Runs 'az network bastion tunnel')</i>"]:::client
        BastionA["Azure Bastion<br><i>(Standard or Premium SKU)</i>"]:::bastion
        API1["AKS Private API Server<br><i>(Private IP Address)</i>"]:::cluster
        
        Local1 -- "1. Native Client Proxy<br>(Port Forwarding)" --> BastionA
        BastionA -- "2. Secure Internal Tunnel" --> API1
    end

    %% Spacer
    Spacer[ ]:::internet
    ScenarioA ~~~ Spacer
    Spacer ~~~ ScenarioB

    %% Scenario B
    subgraph ScenarioB ["Scenario B: Jump-box VM Approach (Works with Developer/Free SKU)"]
        direction LR
        Browser["Local Machine<br><i>(Web Browser)</i>"]:::client
        BastionB["Azure Bastion<br><i>(Developer, Basic, or Standard SKU)</i>"]:::bastion
        JumpBox["Jump-box VM<br><i>(Linux / Windows inside VNet)</i>"]:::jumpbox
        API2["AKS Private API Server<br><i>(Private IP Address)</i>"]:::cluster
        
        Browser -- "1. HTTPS (Azure Portal)" --> BastionB
        BastionB -- "2. SSH / RDP Session" --> JumpBox
        JumpBox -- "3. Executes 'kubectl'" --> API2
    end
```

### Scenario Breakdown

#### Scenario A: Direct API Server Tunneling
*   **Best for:** Developers who want a seamless, native local terminal experience when running `kubectl` commands.
*   **How it works:** The Azure CLI's Native Client feature connects to Azure Bastion, which sets up a proxy tunnel directly linking your local `localhost` port to the private IP of the AKS API Server.
*   **Requirements:** You *must* use the paid **Standard or Premium SKU** of Azure Bastion, as the Developer (free) and Basic tiers do not support the Native Client feature.

#### Scenario B: Jump-box VM Approach
*   **Best for:** Cost-optimized environments (like a homelab), tightly controlled enterprise environments, or when client laptops are untrusted.
*   **How it works:** You log into the Azure Portal via your web browser, use Bastion to start a secure SSH or RDP session into a Jump-box VM residing inside your virtual network, and execute `kubectl` commands directly from that VM.
*   **Requirements:** This scenario is compatible with the free **Developer SKU**, as well as all other paid tiers. It requires maintaining a separate Jump-box Virtual Machine.
