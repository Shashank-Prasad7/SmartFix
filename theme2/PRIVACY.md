# Privacy and data handling

This prototype is intended for the supplied PRISM samples and synthetic test
data. It has not been approved for real customer records. Do not enter names,
contact details, account identifiers, credentials, or confidential source text.
There is no general personal-data detector or redactor.

## Where request data goes

- The browser sends the complaint and supplied article to this API. The console
  keeps its state in memory; it uses no analytics, browser storage, or external
  font service. Copying a response to the clipboard requires the user's action.
- In `PRISM_LLM_MODE=local`, the inference path makes no provider request.
- In `PRISM_LLM_MODE=gemini`, the normalization stage sends complaint text to
  Google's Gemini API. The structuring stage sends source-derived procedure
  titles, steps, categories, and references. Credentials go in the HTTPS header,
  never in the prompt. There is no web grounding or tool execution.
- The server's SQLite cache stores raw complaints, source blocks, compatibility
  fields, and generated guides under `theme2/.runtime/` by default. It is not
  encrypted by the application. Tables are bounded to 10,000 rows each, but
  there is no time-based expiry. Entries can persist across restarts.

Google's [Gemini API terms](https://ai.google.dev/gemini-api/terms) distinguish
paid and unpaid services. Unpaid-service content may be used to improve products
and reviewed by people; those terms prohibit submitting sensitive, confidential,
or personal information. Paid-service terms say prompts/responses are not used
for product improvement; that does not imply zero retention. The actual account
tier and applicable data controls must be checked before hosted evaluation.

## Logs and access

Application errors use generic messages, and request validation errors omit
submitted input. Application code does not log prompts, source text, API keys,
or provider response bodies. Uvicorn's default access logs can record client IP
addresses and request paths; a hosting provider or tunnel can have its own logs.
Use `--no-access-log` when those records are unnecessary.

PRISM's Theme 2 FAQ requires the judge API to work without authentication.
The prototype therefore has no user accounts or tenant separation. The
preview returns evidence for the current supplied article. Expose this service
only with the intended evaluation data and protect the host and its cache files.
The cache directory is not served as a static resource.

After an evaluation, stop the server before removing the configured cache
database and its matching `-wal`/`-shm` sidecars. Remove approved benchmark
captures from local reports when they are no longer needed. Use the host's
filesystem permissions and disk encryption for any retained local files.

## Repository publication

Environment files, runtime databases, logs, dependencies, and generated draft
artifacts are ignored. Public source includes organizer-supplied fixtures and
team-authored synthetic cases; the official source bytes remain unchanged.
Do not place credentials in any source file, commit message, or Git remote URL.
Git author and committer names/emails are public metadata when a branch is
pushed to a public repository. Removing a file later does not erase its history.

Final reviewed submission artifacts must be explicitly added to the tagged
commit under PRISM's submission rules. Review personal details and document
metadata before including them; keep working copies and raw logs ignored.
