# Development

Requires Python 3.11+, no third-party packages (only `pyyaml` for manifests;
tests use stdlib + pytest).

```powershell
python -m pytest -q
```

Private data (official DB + audit CSVs) lives in `data/local/` (gitignored).
With the sibling `audit/` workspace present, refresh it via `review`.
Never commit `*.sqlite`, bulk game data, DLLs, or research clones.

Native CE experiments live in the sibling `CivilizationVI_CommunityExtension-x10-spike`
clone, never in this tree. See `docs/COMMUNITY_EXTENSION_EVALUATION.md`.
