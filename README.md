# Atomic shared data

The data both Atomic apps read, kept once. It is a git submodule at `shared/` in
[Atomic-Periodic-Table.Android](https://github.com/JLindemann42/Atomic-Periodic-Table.Android) and
[Atomic-Periodic-Table.Windows](https://github.com/JLindemann42/Atomic-Periodic-Table.Windows).
Before this, each app held its own copy and they had drifted: the Windows copy of the element files
carried 121 isotopes, 30 CAS numbers and NFPA ratings that Android never received.

| Folder | What | Read by |
|---|---|---|
| `elements/` | `elements_{lang}.json` for the twelve shipped languages | Android app assets and unit tests; Windows app content and `Atomic.Core.Tests` |
| `corpus/` | The Ask Atomic acceptance corpus, 31 TSV files | Android `CorpusTest`, Windows corpus tests. Both apps must pass every row. |
| `golden/` | Tokenizer golden files, generated from the Kotlin tokenizer | Windows `TokenizerGoldenTest` |

## Rules

- **Change data here, never in an app.** Edit, commit and push here, then bump the submodule in
  both apps in the same sitting, so neither ships data the other has not been tested against.
- **The corpus is the gate.** A change that adds behaviour adds rows that fail without it; no change
  may make a row that passed fail.
- **Line endings** follow `* text=auto`, as in both app repositories: LF in the repository, the
  platform's convention in the working copy. Scripts that rewrite the element files should keep the
  working copy's line endings, or every line shows as changed.
- **Not here:** the reference dataset tables (constants, equations, ions and so on). Those are
  Kotlin source in the Android app and the Windows tables are generated from them by
  `tools/port/kt2cs_model.py`, so they already have a single source; CI checks the generated files
  are current.

## Updating an app to the latest data

```bash
git submodule update --remote shared
git add shared
git commit -m "Update shared data"
```

A fresh clone of either app needs `git clone --recurse-submodules`, or `git submodule update --init`
after cloning.
