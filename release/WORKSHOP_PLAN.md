# Workshop publication plan (NOT EXECUTED — human approval required)

Two items. Engine FIRST, then controller. Both start Unlisted.
No upload tooling is automated here; uploads use the Civ VI/Steam
Workshop uploader against the exact `release/out/1.0.0-rc1`-style
staging folders (regenerated final, not RC, at publication time).

## Item 1 — X10 CE Engine (upload first)

- Title: `X10 CE Engine`
- Description: `release/workshop-engine.md` (dependency-focused)
- Staging folder: `workshop/X10-CE-Engine`
- Modinfo version integer: 1
- Visibility: Unlisted
- Preview image: required by the uploader (PNG/JPG, see §preview);
  placeholder acceptable for the unlisted test
- DLC metadata: Gathering Storm required
- After upload: record the numeric Steam Workshop item ID in
  publication state; verify subscribe/install yields exactly the
  staged file set.

## Item 2 — X10: Configurable Semantic Multiplier (upload second)

- Title: `X10 - Configurable Semantic Multiplier`
- Description: `release/workshop-controller.md`
- Staging folder: `workshop/X10`
- Modinfo version integer: 1
- Visibility: Unlisted
- Preview image: required (same spec)
- DLC metadata: Gathering Storm required; Windows-only warning in text
- Steam Required Items: add the engine item ID from step 1 (this is
  SEPARATE from the Civ VI `<Dependencies>` Mod-ID relationship, which
  already exists in `X10.modinfo` and is not a substitute)
- After upload: subscribe to the controller alone and verify Steam
  pulls the engine automatically; verify exactly two folders install
  with no duplicate/old Mods copies; launch smoke test + save/reload
  expecting lifecycle 801/209.

## Critical sequencing

1. Engine uploaded (unlisted) → item ID obtained.
2. Engine ID added as Steam Required Item on the controller draft.
3. Controller uploaded (unlisted).
4. Subscription/install flow verified.
5. Public visibility ONLY on explicit human approval (never automatic).

## Preview image (human/content blocker)

The uploader requires a preview image per item; reliably established
constraints: PNG or JPG, under 1 MB, at least 512x512 px; square
1024x1024 recommended. A simple placeholder is acceptable for unlisted
testing; final artwork is a human task. The `-PublishReady` assembler
gate requires `release/preview-engine.png` + `release/preview-controller.png`
to exist — they do not yet, so publish-ready generation is correctly
blocked. Do NOT invent dimensions beyond the above.
