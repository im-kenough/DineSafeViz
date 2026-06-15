# Architecture Design planning

## Architecture Style
The DineVizSafe application considers Design solutions from the Azure Architecture Centre. It 

The context of this repo is to demonstrate good DevOps and Cloud Systems Engineering practices, so I'll be deploying this in AKS.

The app is a N-tier architecture, single-region, with role-segmented data-tier access and a shared-database read pattern between the application and the analytics dashboard.

### Best practices

- Use autoscaling to handle changes in load. For more information, see Autoscaling best practices.
  - Will use AKS

- Use asynchronous messaging to decouple tiers.
- Cache data that doesn't change often. For more information, see Caching best practices.

- Configure the database tier for high availability by using a solution such as SQL Server Always On availability groups.

- Place a WAF between the front end and the internet.

- Place each tier in its own subnet, and use subnets as a security boundary.
- Restrict access to the data tier by allowing requests from a middle tier only.
  - Don't want to pay for a load balancer

## [Design Principles](https://learn.microsoft.com/en-us/azure/architecture/guide/design-principles/) for Azure Applications

### Core Principles
- Design for self-healing
  - health checks are built into the app and will plug into a future monitoring solution
  - Utilizing AKS will provide self healing in some areas
- Make all things redundant
  - Utilizing AKS will provide self healing in some areas
  - DB read replicas will provide resiliency
  - DR region is in roadmap
- Minimize coordination
  - Dependencies are minimized where practical.
  - Will use Terraform with state saved to Azure Blob to maintain infrastructure consistency
- Design to scale out
  - AKS and VMSS are used to horizontally scale out. This is a demo application, so serious traffic is not expected.
- Partition around limits
  - DineSafeViz has a small footprint and will not approach Azure feature limits.

### Operational Principles
- Design for operations
  - IAC will be implemented to consistently deploy app
  - Monitoring, Centralized logging, Observability is on the road map, which will facilitate incicent response
- Use managed services
  - Will consider PaaS depending if a free / low cost tier is available
- Use an identity service
  - will use Managed Identities to ...

### Strategic principles
- Design for evolution
  - an automated CI/CD pipeline with robust IAC will allow the app to accomodate future growth and design changes
- Build for the needs of business
  - Business Objectives:
  - To be determined
    - Recovery Time Objectives (RTOs)
    - Service Level Agreements (SLAs)
    - Service Level Objectives (SLOs)
    - Maximum Tolerable Outage (MTO)
- Perform failure mode analysis for services
  - to do: conduct failure mode analysis (FMA) during architecture and design phases. Rate each failure mode by risk and impact, then determine appropriate response and recovery mechanisms.



## [Technology choices](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/technology-choices-overview) for Azure solutions

### Choose a compute service

Q: What compute service do I choose?

A: AKS

This app will use Azure Kubernetes Service.

[Considerations](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/compute-decision-tree)

![Choose AKS](/docs/img/choose-aks.png)

Azure Virtual Machines: yes this application can be totally hosted on a simple VM with load balancers and a WAF placed in front of it, but the point is to illustrate DevOps skills


Azure APp Service:

Azure Functions:

Azure Kubernetes Service: chosing this to demonstrate a widely used enterprise tool.

Azure Container Instances: My image can be run on ACI, but is the infrastructure is managed, defeating the purpose

Azure Red Hat OpenShift: Not applicable. Not using Openshift

Azure Batch: Not applicable. Not a HPC app

Azure VMWare Solution: Not applicable. Not a VMware workload.

#### Traditional [Web App vs Single Page App](https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/choose-between-traditional-web-and-single-page-apps)

DineVizSafe is a traditional web app.
- Every page is read only. No user creates, edits or submits data
- No auth wall. Public URL & Static URLs per page
- Inspections are a table, home is a stats & the dashboard is an iframe

There's no 

### Choose a container option

You can use multiple methods to build and deploy containerized applications in Azure. The following articles can help you evaluate container services.

- Choose an Azure container service: Evaluate which Azure container service best suits your specific workload scenarios and requirements.

- Compare Azure Container Apps with other Azure container options: Learn when to use Container Apps and how it compares to other container options, including Azure Container Instances, Azure App Service, Azure Functions, and Azure Kubernetes Service (AKS).

- Choose a Kubernetes at the edge compute option: Learn about trade-offs and considerations for various Kubernetes options for extending compute at the edge.



### Choose a hybrid service

### Choose a data store

### Choose an analytics solution

### Choose an AI service

Not applicable.

### Choose a networking service


### Choose a messaging service

Not applicable.
