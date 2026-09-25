# PRISM and privacy review — 25 September 2026

Decision: ready for a development pull request after the local review fixes.
Final PRISM submission remains incomplete. No push, PR, deployment, release
tag, provider inference, or billing action was performed during this review.

## Sources and scope

Reviewed the supplied PRISM brief (Theme 2 on page 5; submission rules on pages
11–13), FAQ v4 (general submission Q17–20 and Theme 2 requirements), source,
Git history available in the local clone, and the files added by this branch.
The base is `fa7acd9`. This clone is shallow; history beyond its available base
was not independently retrieved. The existing base was already on the team repo.

## Official requirements

| Requirement | Current evidence / remaining work |
|---|---|
| Public or shared GitHub repo with reproducible README and Docker files | Local branch and setup files prepared; frontend dependency install and build passed. Fixed missing `tsconfig.json` in Docker's frontend COPY. Actual container build/launch remains untested because Docker is unavailable here. |
| Two LLM stages, normalization and step structuring; model choice open | Opt-in Gemini stages implemented and mocked. Two different providers are not specified. Live model access, full-source quality, latency, quota, and cost per query remain unmeasured. |
| `/health`, `/v1/troubleshoot`, prescribed JSON, nonempty source-derived steps, exact catalog metadata and no prohibited output URLs | 112 local tests and all 20 official offline contract cases pass. These checks do not establish independent semantic accuracy or public-endpoint behavior. |
| Repeat p95 ≤300 ms, repeat hit rate ≥90%, paraphrase hit rate ≥80%, cold p95 ≤8 s, unseen scenarios | Prior measurements cover local deterministic behavior. The hosted path and actual public endpoint still require evaluation. |
| `results.jsonl`, 8–10 diverse variations per query | A fresh 20-row export with nine generated variations per query passes structural checks. It remains ignored and needs human review and explicit inclusion in the final judged commit. |
| Presentation, video ≤5 minutes, all referenced materials present in tagged commit | Working artifacts and builders exist; final team details, disclosure/signature, visual review, and inclusion in the final commit remain open. |
| Final tag `PRISM_GENAI_HACKATHON_Y2026` | Absent by design until the final reviewed submission is complete. The brief lists 25 September 2026 at 11:59 PM as the deadline; follow any later organizer update. |

The two-reviewer protocol and 60 fully cold observations in `EVAL.md` are team
evaluation targets. They are stronger evidence gates, not additional official
minimum counts quoted from the FAQ.

## Privacy findings and fixes

- Scanned reachable local Git blobs for common provider/GitHub/AWS keys, private
  keys, JWTs, and assigned secrets. Included nested ZIP and Office entries and
  extracted PDF text. No credential matches were detected; pattern scans are
  not a guarantee against every possible secret format.
- No environment secrets, runtime databases, logs, virtual environments, or
  installed dependencies are tracked. Expanded root Git and Docker ignore rules
  for environment variants and key files. Generated evaluation and build files
  remain ignored.
- The supplied personal email is used only in local Git configuration and
  author/committer metadata, as requested. It does not appear in tracked project
  content. Commit metadata will be public when pushed to this public repository.
- Organizer contact addresses and a support address are present in supplied
  documents/fixtures. No additional private customer records were found. Source
  inputs remain byte-preserved. One workstation path remains in the inherited
  base README history; this branch's current README removes it.
- Removed the legacy fallback UI that inserted response strings through
  `innerHTML` and fetched external fonts. An unbuilt checkout now shows a static
  local setup page. The built console renders source text through React.
- Request-validation errors now return a generic 422 without echoing submitted
  fields. Added a regression covering both API endpoints.
- Added a visible data-use notice and `PRIVACY.md`: hosted requests send text to
  Gemini; the local cache is plaintext and has no time-based expiry. Use supplied
  samples or synthetic data. Real customer data requires further privacy work.
- Corrected the hosted timeout budget after admission waiting and tested that
  a consumed deadline starts no provider call. A hard public wall-clock bound
  still requires live validation.

## Verification for this review

- Python tests: 112 passed (one dependency deprecation warning).
- Ruff: passed.
- Fresh offline frontend dependency install, TypeScript, and Vite build: passed.
- Official export: 20/20 contract cases; 20 JSONL rows and 180 generated variations.
- Provenance: 11/11 imported files and 6/6 nested entries match; 4/4 available
  parent originals match (the outer archive is absent from the teammate's root).
- Final diff whitespace check: passed.

Read [PRIVACY.md](../PRIVACY.md) for provider terms and retention details, and
[RELEASE_STATUS.md](RELEASE_STATUS.md) for the remaining submission gates.
