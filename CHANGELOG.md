# Changelog

## 2.4.4 — 2026-10-27

- Encode search terms as one path segment, including literal slashes and hashes.
- Read video metadata from JSON-LD arrays and graph objects.
- Handle empty profiles without dividing by zero and close profile scrapers when iteration stops early.
- Close CLI sessions and report unsuccessful downloads as errors.
- Use the published `eaf-base-api>=4.2.5` dependency.

