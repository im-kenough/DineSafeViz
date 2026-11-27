# DineSafeViz

## 1. Introduction
DineSafeViz is a containerized web app that builds inspection reports and
interactive analytics from Toronto Public Health's food safety data.

The app retrieves and parses the DineSafe dataset (Toronto Public Health's food
safety program) from the City of Toronto's Open Data Portal.

![DineSafeViz home page](docs/archived/docs/img/root-readme/dsv-home-1.png)

## 2. Features

### 2.1 Search

Type in a restaurant name to see their inspection record for any health code violations.

![Inspection results page](docs/archived/docs/img/root-readme/dsv-inspect-1.png)

### 2.2 Analytics dashboard

Explore and get a statistical breakdown of **over 26 years** of inspection data.

![DineSafeViz analytics dashboard](docs/archived/docs/img/root-readme/dsv-dash-1.png)

### 2.3 Inspections data

See a daily breakdown of which establishments were inspected and their results.

## 3. Application Architecture

Show basic logical diagram of the application

Technology stack

| Layer          | Technology                               |
| -------------- | ---------------------------------------- |
| Web app        | Python, Flask, Gunicorn                  |
| Database       | PostgreSQL                               |
| Analytics      | Grafana                                  |
| Reverse proxy  | nginx                                    |
| Containers     | Docker, Docker Compose                   |

## 4. Infrastructure

Show basic logical diagram of the physical infra (azure diagram)

## 5. Automation

### 5.1 CI - Continuous Integration

### 5.2 CD - Continuous Delivery

## 6. AI™️ 🌈

Built using Claude Code, leveraging skills, worklows and software factories. 

Integrated Claude into Github Actions to perform:
- code review
- security review
- issue labeling

## n. Repository structure

Include a breakdown of the repo structure