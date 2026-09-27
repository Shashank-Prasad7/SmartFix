# Working rules for this project

- Use this directory as the project root. Put new code, tests, dependencies, generated assets, logs, reports, and submission files inside it.
- Treat the parent directory's hackathon kit, brief, FAQ, templates, and existing planning/experiment files as read-only inputs. Do not move, overwrite, format, delete, or regenerate them without a separate explicit user request.
- Read README.md, PLAN.md, SPEC.md, and EVAL.md before implementation. This folder's PLAN.md is the current working plan; the parent copy is a preserved snapshot.
- Import only required kit entries into `data/official/`, preserving their bytes and provenance hashes. Never edit the original archive or supplied schema to make an output pass. Create synthetic fixtures separately and label them.
- Reuse earlier experiments selectively only after reviewing them. Their paths and assumptions may refer to the parent workspace. Do not run legacy report-writing scripts against the protected parent directories; adapt copies here first.
- Keep SPEC and EVAL consistent with PLAN. Do not silently add features, change official output policy, or substitute easier metric denominators.
- Configure local writable caches, build outputs, and temporary artifacts under this directory. Use project-local environments or existing read-only bundled runtimes; avoid modifying shared runtimes.
- Keep credentials and sensitive request contents out of source, logs, and reports. Ignore secrets, runtime state, dependency caches, and build outputs before committing any implementation.
- Use project-scoped Git operations; do not stage unrelated parent files or create a nested repository. Never use broad cleanup/deletion commands against the parent workspace.
- Preserve the source boundary, the full-article official-output default, explicit unknown facts, immutable catalog metadata, and safe cache compatibility rules.
- Documentation work does not authorize provider calls, billing activation, hosting, or application implementation. Perform those only when the user requests the corresponding build/evaluation work.
- Report measured results separately from targets. A valid schema, source reference, or passing mocked test is not proof of semantic accuracy, live latency, or hackathon performance.
