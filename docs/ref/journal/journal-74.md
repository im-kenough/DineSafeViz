# Journal 74

## 2026-05-19 — Feat: Skip ISO download and add `--force-download` to `bake-seed`

**Summary:** The `bake-seed` command failed with an API upload timeout because Packer was downloading the Ubuntu ISO to the local workstation and then attempting to push the 3.17 GB file over the Proxmox API.

**Diagnosis:**
The `ubuntu-seed.pkr.hcl` used the default `iso_url`, which instructs Packer to download the ISO locally. When it tried to upload the downloaded file to Proxmox, it hit a `use of closed network connection` error, likely due to a timeout or connection limit over the Proxmox API.

**Resolution:**
Updated `ubuntu-seed.pkr.hcl` to use `iso_download_pve = true`. This instructs the Proxmox node to download the ISO directly from the internet to its own datastore. This avoids the workstation-to-Proxmox API upload entirely, which was causing timeouts.

Introduced a `--force-download` flag that appends a `timestamp()` query parameter to the `iso_url` and sets `iso_checksum = "none"`. This forces Proxmox to treat the URL as new and re-download the ISO, bypassing its internal cache.

**Files changed:**
- `infra/packer/ubuntu-seed.pkr.hcl` — Added `force_download` variable; updated `boot_iso` to use `iso_download_pve = true` and conditional cache-busting logic.
- `infra/Makefile` — Added handling for the `--force-download` flag and exported `PACKER_CACHE_DIR` for local fallback safety.
