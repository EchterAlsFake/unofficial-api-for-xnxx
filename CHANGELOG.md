# 3.0.0

Release 3.0.0

Update pagination handling, validation, and documentation.

Changes since v2.4.5:

```text
README.md                  | 14 ++++++++
 pyproject.toml             |  4 +--
 xnxx_api/api.py            | 88 +++++++++++++++++++++++++++++-----------------
 xnxx_api/modules/consts.py |  9 +++++
 4 files changed, 80 insertions(+), 35 deletions(-)
```

# Changelog

## 2.4.5 - 2026-11-14

- Qualify structured upload dates and stop exposing page-comment timestamps as publication dates.

## 2.4.4 — 2026-10-27

- Encode search terms as one path segment, including literal slashes and hashes.
- Read video metadata from JSON-LD arrays and graph objects.
- Handle empty profiles without dividing by zero and close profile scrapers when iteration stops early.
- Close CLI sessions and report unsuccessful downloads as errors.
- Use the published `eaf-base-api>=4.2.5` dependency.

