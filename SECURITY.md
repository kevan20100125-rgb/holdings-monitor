# Security Policy

## Supported versions

This repository is intended as a public side project starter. Only the latest main branch is considered supported.

## Reporting a vulnerability

Do not open a public issue for credential exposure, token leakage, or an exploitable flaw.

Instead:
1. Rotate any affected secrets immediately.
2. Remove exposed credentials from git history before disclosure.
3. Contact the maintainer privately and provide a minimal reproduction.

## Baseline security requirements

- Never commit `.env`, database files, logs, raw source exports, or generated CSV/XLSX files.
- Store notification credentials only in environment variables or deployment platform secret stores.
- Pin third-party GitHub Actions to full commit SHAs before production use.
