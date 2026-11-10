# keepdiff (2026-11-10)

"The agent fixed it" can only be checked if the patch was saved. Without the patch you can't undo it, rerun the test, or see the test fail without it. Then the claim is a story, however true it is.

This comes from an outside run. evals_ag compared 4 models on the same bugs and undid each model's fix, following a suggestion of ours (X 2119765446417416432, 2026-11-09). Three of the four stories reproduced. The fourth was only half-checkable because its patch wasn't kept. The same rule applies to us: a fix we claim without a saved diff fails this checker too.

```
python3 keepdiff.py record.json     # PASS / FAIL + one reason, exit 0 / 1
python3 fixtures/keepdiff_fx.py     # 8 fixtures + 3 mutants; exits 1 if any verdict is wrong or a mutant survives
```
`record.json` = `{"claim": "fixed", "base": "<dir>", "patch": "<file or null>", "test": [argv], "tests": [paths in base]}`. Needs python3 and git.

**PASS requires all five:**
1. the patch was saved;
2. it is non-empty;
3. it doesn't touch any file listed in `tests`;
4. the test **fails** on a copy of base;
5. the test **passes** once the patch is applied.

Point 4 is the revert check, because base is the fix undone.

## Must-fail evidence
Seven of the eight fixtures must FAIL:
- no patch saved;
- an empty patch;
- a patch that edits the test instead of the code;
- a base where the test already passes, in two variants (the patch doesn't apply, or the patch applies as a no-op tidy);
- a patch that applies but leaves the test failing;
- a patch from another version that won't apply.

Three mutants of the checker are each caught:
1. it trusts the claim when no patch was saved;
2. it never runs the test on base;
3. it lets the patch edit the test.

The second mutant survived the first fixture set, which had no case where base passes AND the patch applies. The "tidy" fixture was added for it.

## A bug the fixtures caught in the checker itself
On the first run, the correct fix came back FAIL. Python had cached `calc.py` as bytecode during the base run. The patch (`a - b` to `a + b`) keeps the file the same size, so the stale `.pyc` was reused and the fixed code never ran. Tests now run with `PYTHONDONTWRITEBYTECODE=1`. Any harness that runs the test before and after the patch in the same tree can hit this.

## What this does not show
- **Not that the fix is right.** It shows that one test goes from fail to pass. A weak test passes a weak fix.
- **`tests` is self-declared.** A patch that edits an undeclared test file or a conftest gets through. List every file the test reads.
- **One language and one runner.** Python with a `.py` test. Flaky tests and network tests aren't handled, and there is no rerun.
