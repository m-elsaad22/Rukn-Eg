# SEO content audit

`seo_content_audit.py` fetches every published post and page from the Egypt WordPress REST API (or local import CSVs) and flags thin copy, shared templates, near-duplicates, search-intent mismatches, and missing SEO structure.

Stdlib only. Do not put application passwords in this repo.

```bash
export WP_USER='...'
export WP_APP_PASS='...'   # spaces optional
python3 scripts/seo_content_audit.py --source rest --out-dir reports --cache /tmp/wp-egypt-posts-cache.json
```

CSV fallback (import files in the repo root):

```bash
python3 scripts/seo_content_audit.py --source csv --out-dir reports
```

Outputs:

- `reports/seo-content-audit.csv` — one row per URL
- `reports/seo-similar-pairs.csv` — similar URL pairs
- `docs/egypt-seo-content-audit.md` — executive report
