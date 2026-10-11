# Workshop page draft — X10: Configurable Semantic Multiplier (NOT YET UPLOADED)

Name: `X10 - Configurable Semantic Multiplier`
Teaser: `Scale certified game numbers by any multiplier (default x10), per-module toggles. Requires X10 CE Engine.`

Description:
> THIS IS THE MAIN ITEM. Subscribing here should automatically pull in
> the required "X10 CE Engine" item (set as a Steam Required Item);
> enable BOTH, and no other Community Extension / GameCore replacement.
>
> X10 multiplies certified numeric game effects by the multiplier you
> choose. Configure in game setup under Game Options: X10_MULTIPLIER
> (0-100, default 10, e.g. 7.3; 0 turns the multiplier off) plus seven
> per-module toggles (traits, policies, governments, pantheons,
> wonders, governors, suzerain), all default ON.
>
> Whole-unit bonuses (charges, power, granted resources, ...) are only
> applied for exact whole-number results; fractional results keep their
> official values instead of rounding.
>
> KNOWN INTENTIONAL EXCLUSIONS: percentage-factor scaling, healing caps,
> unique-improvement intrinsics, and other ambiguous mechanics stay at
> official values (full list: release/KNOWN_ISSUES.md in the source).
>
> Requirements: Windows x64 ONLY and Gathering Storm. Affects saved
> games: enabling/disabling mid-campaign changes definition values.
>
> Troubleshooting: after reaching the map, check
> `%TEMP%\X10Lifecycle.log` for `writes=` / `post_add_match=` lines.
>
> License AGPL-3.0. Source, build instructions, validation summary:
> SOURCE.txt / VALIDATION.md in the release source
> (planned: https://github.com/Dacilla/civ6-x10-release-source).

Required items: X10 CE Engine (Steam "Required Items" + Civ VI
`<Dependencies>` on Mod ID 397f2070-dfde-4124-88ce-e34249fc8190).
