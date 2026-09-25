# Official input copies

These are byte-preserving copies of the supplied hackathon materials. Use this directory for project-local references and input loading. Parent originals remain unchanged and are not required runtime paths.

## Inventory

| Location | Contents |
|---|---|
| `documents/` | Official hackathon brief PDF and FAQ DOCX |
| `templates/` | Supplied submission PPTX and AI disclosure DOCX |
| `archives/participant-kit-all-themes.zip` | Complete original participant archive |
| `archives/Theme02_Input_Kit.zip` | Exact nested Theme 2 archive |
| `student_kit/siis_responses.json` | Canonical SIIS queries/articles |
| `student_kit/deeplinks.json` | Immutable deep-link catalog |
| `student_kit/schema.py` | Supplied response schema |
| `student_kit/input.txt` | Supplied input list; canonical exports still use SIIS `original_query` |
| `student_kit/sample_output.json` | Supplied example; FAQ constraints take precedence over its formatting discrepancies |

[manifest.json](manifest.json) records all 11 copied/extracted files, their SHA-256 digests, byte sizes, and source filenames or archive entries. Paths in that manifest are relative to this directory. It is an integrity/provenance record, not a semantic validation or benchmark result.

## Handling rules

- Keep these baseline files unchanged, especially the schema, catalog, and source articles.
- Make filled/edited template copies in `../../submission/`; do not overwrite the baseline templates here.
- Put annotations and synthetic variants in `../annotations/` and `../fixtures/`, not in `student_kit/`.
- Only the five Theme 2 inputs were extracted. The unrelated Theme 5 harness remains inside the complete outer archive and is not the Theme 2 evaluator.
- Use project-relative paths resolved from the project root, not absolute paths to the original author's machine.
- Do not publish supplied materials more broadly than permitted by the organizer's submission/sharing terms.
