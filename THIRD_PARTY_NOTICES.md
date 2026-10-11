# Third-party notices

This repository contains no third-party code. Research sources consulted
(clones live outside this tree, never vendored):

- Community Extension — Wild-W/CivilizationVI_CommunityExtension (AGPL;
  accepted dependency/foundation for X10). Workshop ID 3277976174, v1.3.
- Civ VI GameCore reference — cru121/civ6-gamecore-reference (see its LICENSE).
- Dev CE research — cru121/civ6-dev-ce (see its LICENSE).
- Firaxis game data: raw copied official runtime database/data files
  (`data/local/`, never redistributed) are used locally as an input. The
  public package necessarily contains narrowly derived identifiers/guard
  values in the registry/bridge (see `docs/RELEASE_HARDENING.md` §2 for
  the exact engineering policy).

A future `docs/CE_UPSTREAM_PROPOSAL.md` will be reviewed here before any
upstream contact.

## Release-context note (Phase 7A review)

The "no third-party code" claim above describes this source repository
(the GameCore DLL is built from the external CE fork, never vendored
here). A Workshop runtime bundle's DLL *is* built from AGPL-3.0 fork
source (`Wild-W/CivilizationVI_CommunityExtension` @ `0655190` +
X10 native changes), so the 7B release package must carry its own
license/notice bundle (AGPL-3.0 text + fork source reference + DLL hash)
rather than relying on this file. See `docs/RELEASE_HARDENING.md` §4.
