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
