# Initial evaluation baseline

Date: 23 September 2026. Commands were run before implementation changes,
except for dependency installation needed to collect tests.

## Toolchain and first attempt

`python --version` failed because `python` was not on PATH. The bundled Python
3.12.14 initially had no pytest, FastAPI, `rank_bm25`, or
`sentence_transformers`. `python tests/run_eval.py` from the old `codes/`
directory failed at import:

```text
File ".../theme2/codes/tests/run_eval.py", line 13, in <module>
  from theme2.src.pipeline import TroubleshootingPipeline
ModuleNotFoundError: No module named 'theme2'
```

After installing declared Python dependencies into `theme2/.venv`, this command
ran from `theme2/`:

```text
.venv/Scripts/python.exe -m pytest codes/tests -q
0 tests collected; 3 collection errors in 1.27s
ERROR codes/tests/test_api.py: RuntimeError: starlette.testclient requires httpx2
ERROR codes/tests/test_cache.py: ModuleNotFoundError: No module named 'theme2'
ERROR codes/tests/test_contracts.py: ModuleNotFoundError: No module named 'theme2'
```

After moving `codes/src` and `codes/tests` into the package layout and adding
the TestClient transport, collection exposed a second missing dependency:

```text
0 tests collected; 2 collection errors in 1.53s
ERROR theme2/tests/test_api.py: ModuleNotFoundError: No module named 'sentence_transformers'
ERROR theme2/tests/test_cache.py: ModuleNotFoundError: No module named 'sentence_transformers'
```

With a local lexical fallback, tests ran and yielded 10 passes and one failure:

```text
FAILED theme2/tests/test_cache.py::test_paraphrase_cache_hit
AssertionError: assert 'miss' in ('semantic_hit', 'exact_hit')
1 failed, 10 passed
```

That test supplied a different article than the prior seed, so a cache miss was
required by SPEC S07. The fixture now seeds a genuine same-source paraphrase
and independently checks changed-source and changed-operation guards.
