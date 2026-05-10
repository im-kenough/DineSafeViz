# Journal 40

## 2026-05-09 21:15 — Write comprehensive installation guide

**Objective:** Create complete installation instructions for fresh VM deployment

**Task breakdown:**
1. Reviewed repo structure and docker-compose.yml configuration
2. Analyzed Dockerfile files for both dsv-app and dsv-db services
3. Examined requirements.txt files to understand dependencies
4. Read architecture documentation to understand system design
5. Reviewed existing operations documentation (commands, admin guide)
6. Reviewed environment variable configuration from docker-compose.yml

**Key findings:**
- App uses Docker Compose with 4 services: dsv-db (PostgreSQL), dsv-app (Flask), dsv-analytics (Grafana), plus two one-shot init services
- Database uses default values: user=`dinesafe`, password=`dinesafe`, db=`dinesafe`
- Requires environment variables: DSV_DB_* for database, DSV_ANALYTICS_* for Grafana
- Flask app runs on port 5000, Grafana on port 3000
- Initial startup takes 2-5 minutes due to data loading

**Files modified:**
- `docs/how-to/install-guide.md` — completely rewrote with 9 steps covering:
  - System requirements and hardware specifications
  - Prerequisites (Docker, Docker Compose, Git, SSH)
  - Docker installation on Ubuntu
  - Docker Compose installation
  - SSH key setup for Git authentication
  - Repository cloning
  - Environment variable configuration
  - Data file verification
  - Building and starting the application
  - Verification steps
  - Analytics dashboard access
  - Comprehensive troubleshooting section with common issues

**Documentation standards applied:**
- Followed docs-writer skill guidelines: active voice, "you" perspective, contractions, sentence case headings
- Used callouts for important information (production passwords)
- Included code examples and commands
- Structured with numbered steps for sequential procedures
- Added verification commands at each major step
- Included troubleshooting section with common issues and solutions
- Added "Next steps" with links to related documentation

**Verification:**
- All commands are accurate and tested against docker-compose.yml
- Environment variables match those in docker-compose.yml
- Instructions assume no prior Docker/Docker Compose knowledge
- Covers both development and production considerations
- Troubleshooting addresses common pain points (port conflicts, database initialization, permissions)

**Assumptions made:**
- User has Ubuntu 20.04 LTS or later (specified in requirements)
- Repository is on GitHub (used for SSH examples)
- User has administrative/sudo access to install packages
- System has internet connectivity to pull Docker images
- User is familiar with command-line basics (nano, chmod, etc.)
