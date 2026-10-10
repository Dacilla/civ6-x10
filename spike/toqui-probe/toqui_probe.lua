-- Toqui/pressure observability probe (DISPOSABLE, Phase 6A research).
-- Answers ONE question: do the eight NEEDS_LIVE_PROBE identity-pressure
-- definitions read back through the current store-lookup mechanism?
-- The authoritative evidence is the native "stored_after_add ... MATCH
-- via=store-lookup" (or blank/unreadable) line in %TEMP%\X10Lifecycle.log;
-- this Lua readback is corroboration only. NEVER ship this file; it is not
-- referenced by any .modinfo in this directory.

local TARGETS = {
  -- {definition id, argument, official}
  { id = "TOQUI_DOMESTIC_LOYALTY", arg = "Amount", official = "4" },
  { id = "TOQUI_FOREIGN_LOYALTY", arg = "Amount", official = "4" },
  { id = "CARDINAL_BISHOP_PRESSURE", arg = "Amount", official = "100" },
  { id = "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_3_LOYALTY_FROM_COUNTERSPY", arg = "Amount", official = "4" },
  { id = "MINOR_CIV_PRESLAV_ARMORY_IDENTITY_BONUS", arg = "Amount", official = "2" },
  { id = "MINOR_CIV_PRESLAV_BARRACKS_STABLE_IDENTITY_BONUS", arg = "Amount", official = "2" },
  { id = "MINOR_CIV_PRESLAV_MILITARY_ACADEMY_IDENTITY_BONUS", arg = "Amount", official = "2" },
  { id = "MINOR_CIV_VATICAN_CITY_GREAT_PERSON_RELIGIOUS_PRESSURE", arg = "Amount", official = "400" },
}

local raw = GameConfiguration.GetValue("X10_MULTIPLIER")
if raw == nil then
  error("[X10ToquiProbe] FATAL: X10_MULTIPLIER missing from GameConfiguration")
end
local k = tonumber(raw)
if k == nil or k < 0 or k > 100 then
  error("[X10ToquiProbe] FATAL: X10_MULTIPLIER not usable: " .. tostring(raw))
end

local function plog(s)
  if X10Lifecycle ~= nil and X10Lifecycle.LogMsg ~= nil then
    X10Lifecycle.LogMsg(s)
  end
  print(s)
end

plog(string.format("[X10ToquiProbe] configuration X10_MULTIPLIER=%s", tostring(raw)))
if X10Lifecycle ~= nil and X10Lifecycle.Ping ~= nil then
  X10Lifecycle.Ping()
else
  plog("[X10ToquiProbe] WARNING: X10Lifecycle native table absent (engine DLL not active?)")
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
  local expected = official * k
  local handle = seen[t.id]
  if handle == nil then
    plog(string.format("[X10ToquiProbe] %s: runtime handle ABSENT", t.id))
  else
    local value = GameEffects.GetModifierArgumentString(handle, t.arg)
    plog(string.format("[X10ToquiProbe] %s handle=%s %s=%s expected~%.4f",
      t.id, tostring(handle), t.arg, tostring(value), expected))
  end
end
plog("[X10ToquiProbe] done")
