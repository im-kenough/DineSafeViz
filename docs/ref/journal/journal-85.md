# Journal 85: Public Repo Secret Audit

## 2026-06-09 10:00
Starting secret audit before making the repository public.
Goal: Ensure no plaintext secrets in current state or git history.

### Initial Checks
- Checked .gitignore: Covers .env, tfvars, pkrvars, tfstate.
- Checked infra/ansible/group_vars/all.yml: Contains non-secret config as expected.
- Verified secrets.yml location: infra/ansible/vault/secrets.yml.

### To Do
- [ ] Verify infra/ansible/vault/secrets.yml is encrypted.
- [ ] Audit infra/scripts/render-vars.py for secret handling.
- [ ] Search current codebase for plaintext secrets.
- [ ] Search git history for plaintext secrets.
- [ ] Document findings and recommendations.

### Audit Completion
- [x] Verified secrets.yml is encrypted in history.
- [x] Confirmed .gitignore covers all sensitive files (.env, tfvars, pkrvars, tfstate).
- [x] Audited docs and scripts for hardcoded secrets - none found (only dummy/test values).
- [x] Verified src/dsv-db/refresh.py uses safe fallback defaults.

### Conclusion
The repository is safe to be made public. No plaintext secrets were found in the current state or git history.

### Recommendations for Public Repo
1. **Never commit the vault password file.** Ensure no such file is ever added to the repo (currently none exist).
2. **Consider a secret scanner.** Use GitHub's built-in secret scanning (automatic for public repos) or a pre-commit hook like `detect-secrets`.
3. **Internal IPs.** The repo contains internal home lab IPs (e.g., 10.0.20.21). These are safe for public disclosure as they are not reachable from the internet.
