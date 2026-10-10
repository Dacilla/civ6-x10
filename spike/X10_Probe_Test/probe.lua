-- X10 production-candidate diagnostic probe (TEMPORARY, local test builds).
-- Configuration comes from X10_MULTIPLIER (never X10_PROBE_K). Fails loudly.
-- Expected values are RECOMPUTED here from official + k (same semantics as
-- the native engine), then compared against runtime readback.

local TARGETS = {
  -- {definition id, argument, official, kind}
  { id = "TRAIT_GOLD_FROM_DOMESTIC_TRADING_POSTS", arg = "Amount", official = "1",  kind = "flat" },
  { id = "TRAIT_LINCOLN_INDUSTRIAL_ZONE_LOYALTY",  arg = "Amount", official = "3",  kind = "flat" },
  { id = "AGOGE_ANCIENT_MELEE_PRODUCTION",         arg = "Amount", official = "50", kind = "flat" },
  { id = "TRAIT_TOQUI_COMBAT_BONUS_VS_GOLDEN_AGE_CIV", arg = "Amount", official = "10", kind = "combat" },
  -- Phase-2 pantheon witness: requires founding God of the Forge in-game.
  -- Absent handle is reported, not failed (see loop below).
  { id = "GOD_OF_THE_FORGE_UNIT_ANCIENT_CLASSICAL_PRODUCTION_MODIFIER", arg = "Amount", official = "25", kind = "flat" },
  -- Phase-3 wonder witness: requires building the Statue of Zeus in-game.
  { id = "STAUEZEUS_ANTI_CAVALRY_PRODUCTION", arg = "Amount", official = "50", kind = "flat" },
  -- Phase-3B direct-bridge witness: Panama Canal helper, created by the
  -- generated bridge SQL (guarded on the audited official Gold=10).
  { id = "X10_PANAMA_CANAL_YIELD_GOLD", arg = "Amount", official = "10", kind = "flat" },
  -- Phase-4C Governor witnesses. Governor promotions need not be active:
  -- an absent handle is reported, not failed. The authoritative proof is the
  -- native "stored_after_add ... MATCH via=store-lookup" line in
  -- X10Lifecycle.log. Do NOT add the five engine-integral Governor rows here —
  -- they intentionally REFUSE at fractional k and must stay out of the
  -- ordinary PASS set.
  -- Base Governor additive (harvest yields 50): native value 365 at k=7.3.
  { id = "GROUNDBREAKER_BONUS_HARVEST_YIELDS", arg = "Amount", official = "50", kind = "flat" },
  -- Base Governor combat (city combat bonus 5): combat formula -> ~24.04.
  { id = "GARRISON_COMMANDER_ADJUST_CITY_COMBAT_BONUS", arg = "Amount", official = "5", kind = "combat" },
  -- Secret Society + supplemental semantic floor (Owls treasury interest 3%):
  -- additive percent -> 21.9 at k=7.3.
  { id = "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_4_GOLD_INTEREST", arg = "Percent", official = "3", kind = "flat" },
  -- Secret Society Ley Line (Hermetic great engineer ley line, requires the
  -- Gathering Storm ruleset mode payload): additive 1 -> 7.3 at k=7.3.
  { id = "HERMETIC_ORDER_GREAT_ENGINEER_LEY_LINE_PRODUCTION", arg = "Amount", official = "1", kind = "flat" },
  -- Phase-5C Suzerain witnesses. City-states need not spawn and Suzerain
  -- status is never earned naturally: an absent handle is reported, not
  -- failed. The authoritative proof is the native "stored_after_add ...
  -- MATCH via=store-lookup" line in X10Lifecycle.log. Do NOT add the nine
  -- Bologna GP-point rows here — they intentionally REFUSE at fractional k
  -- (count-like 1 x 7.3) and must stay out of the ordinary PASS set.
  -- Auckland flat plot yield (base shallow-water production 1): 1 -> 7.3.
  { id = "MINOR_CIV_AUCKLAND_SHALLOW_WATER_PRODUCTION_BONUS_BASE", arg = "Amount", official = "1", kind = "flat" },
  -- Antananarivo percent magnitude (culture per earned great person 2):
  -- additive percent -> 14.6 at k=7.3.
  { id = "MINOR_CIV_ANTANANARIVO_CULTURE_FROM_EARNED_GREAT_PEOPLE_BONUS", arg = "Amount", official = "2", kind = "flat" },
  -- Ngazargamu compound discount (land unit purchase -20%): the DISCOUNT
  -- transform d_k = (1-(1-d)^k)*100 -> ~80.3864 at stored FLOAT32 k=7.3,
  -- never 20 x 7.3 = 146.
  { id = "MINOR_CIV_NGAZARGAMU_BARRACKS_STABLE_PURCHASE_BONUS", arg = "Amount", official = "20", kind = "discount" },
}

local raw = GameConfiguration.GetValue("X10_MULTIPLIER")
if raw == nil then
  error("[X10Probe] FATAL: X10_MULTIPLIER missing from GameConfiguration")
end
local k = tonumber(raw)
if k == nil or k < 0 or k > 100 then
  error("[X10Probe] FATAL: X10_MULTIPLIER not usable: " .. tostring(raw))
end
if k == 0 then
  error("[X10Probe] FATAL: test requires nonzero k (0 means Off)")
end

local function x10(kind, v, kk)
  if kind == "combat" then
    return 25 * math.log(kk * (math.exp(v / 25) - 1) + 1)
  elseif kind == "discount" then
    -- same mathematics as production compound_discount_for_multiplier:
    -- d_k = (1-(1-d)^k)*100, preserving the official sign
    local d = math.abs(v) / 100.0
    local out = (1 - (1 - d) ^ kk) * 100.0
    return v < 0 and -out or out
  else
    return v * kk
  end
end

local function plog(s)
  if X10Lifecycle ~= nil and X10Lifecycle.LogMsg ~= nil then
    X10Lifecycle.LogMsg(s)
  end
  print(s)
end

plog(string.format("[X10Probe] configuration X10_MULTIPLIER=%s", tostring(raw)))
if X10Lifecycle ~= nil and X10Lifecycle.Ping ~= nil then
  X10Lifecycle.Ping()
else
  plog("[X10Probe] WARNING: X10Lifecycle native table absent (engine DLL not active?)")
end

local seen = {}
for _, handle in pairs(GameEffects.GetModifiers()) do
  local definition = GameEffects.GetModifierDefinition(handle)
  if definition ~= nil then
    local did = definition.Id or definition.ModifierId or definition.id
    if did ~= nil then
      seen[did] = handle
    end
  end
end

for _, t in ipairs(TARGETS) do
  local official = tonumber(t.official)
  local expected = x10(t.kind, official, k)
  local handle = seen[t.id]
  if handle == nil then
    plog(string.format("[X10Probe] %s: runtime handle ABSENT (definition write verified natively via stored_after_add)", t.id))
  else
    local value = GameEffects.GetModifierArgumentString(handle, t.arg)
    local vnum = tonumber(value)
    local verdict = (vnum ~= nil and math.abs(vnum - expected) < 0.015) and "PASS" or "FAIL"
    plog(string.format("[X10Probe] %s handle=%s %s=%s expected=%.2f %s",
      t.id, tostring(handle), t.arg, tostring(value), expected, verdict))
  end
end
plog("[X10Probe] done")

-- Phase-3D bridge materialization diagnostic: dump X10BridgeDiag (written by
-- X10WonderBridge.sql immediate statements + deferred triggers) so one live
-- run proves per-cell source state. Lines go through the native logger into
-- %TEMP%\X10Lifecycle.log with the [X10BridgeDiag] prefix.
local function dump_bridge_diag()
  local q = "SELECT helper_id, source_table, source_key, expected, observed,"
    .. " helper_exists, attached, amount_exists, zeroed, origin"
    .. " FROM X10BridgeDiag ORDER BY helper_id"
  local ok, res = pcall(function() return DB.Query(q) end)
  if not ok or res == nil then
    plog("[X10BridgeDiag] UNAVAILABLE (diagnostics query failed)")
    return
  end
  local n_exp, n_mat, n_un = 0, 0, 0
  for _, row in ipairs(res) do
    if type(row) == "table" then
      n_exp = n_exp + 1
      local got = tonumber(row.helper_exists) or 0
      if got == 1 then n_mat = n_mat + 1 end
      if row.observed == nil then n_un = n_un + 1 end
      plog(string.format("[X10BridgeDiag] %s src=%s|%s exp=%s obs=%s"
        .. " helper=%s attach=%s amount=%s zeroed=%s origin=%s",
        tostring(row.helper_id), tostring(row.source_table),
        tostring(row.source_key), tostring(row.expected),
        tostring(row.observed), tostring(row.helper_exists),
        tostring(row.attached), tostring(row.amount_exists),
        tostring(row.zeroed), tostring(row.origin)))
    end
  end
  plog(string.format("[X10BridgeDiag] bridge_expected=%d"
    .. " bridge_materialized=%d bridge_unavailable=%d",
    n_exp, n_mat, n_un))
end
dump_bridge_diag()
