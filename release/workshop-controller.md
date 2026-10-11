# Workshop page draft — X10: Configurable Semantic Multiplier (NOT YET UPLOADED)

Name: `X10 - Configurable Semantic Multiplier`
Teaser: `Scale certified game numbers by any multiplier (default x10), per-module toggles. Requires X10 CE Engine.`

Description:
> X10 multiplies certified numeric game effects by the multiplier you
> choose (default 10; set X10_MULTIPLIER 0-100, e.g. 7.3; 0 turns the
> multiplier off). Seven per-module toggles (traits, policies,
> governments, pantheons, wonders, governors, suzerain) default ON.
>
> Whole-unit bonuses (charges, power, resources, ...) are only applied
> for exact whole-number results; fractional results keep their official
> values instead of rounding.
>
> KNOWN INTENTIONAL EXCLUSIONS: percentage-factor scaling, healing caps,
> unique-improvement intrinsics, and other rows documented in the
> release source stay at official values.
>
> Requirements: Windows x64 ONLY, Gathering Storm, AND the "X10 CE
> Engine" Workshop item (set as a required item; enable both, and no
> other Community Extension GameCore replacement). Affects saved games:
> enabling/disabling mid-campaign changes definition values.
>
> Troubleshooting: after reaching the map, check
> `%TEMP%\X10Lifecycle.log` for `writes=` / `post_add_match=` lines.
>
> License AGPL-3.0. Source, build instructions, validation summary:
> SOURCE.txt / VALIDATION.md in the release source.

Required items: X10 CE Engine (Steam "Required Items" + Civ VI
`<Dependencies>` on Mod ID 397f2070-dfde-4124-88ce-e34249fc8190).
