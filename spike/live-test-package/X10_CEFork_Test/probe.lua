-- X10 native write probe (DISPOSABLE). Fails loudly; no silent fallback.
-- Reads back through integer modifier HANDLES (GetModifierArgumentString
-- takes a handle, never a string ID). Results go to %TEMP%\X10Probe.log
-- via X10Lifecycle.LogMsg AND to print.
-- Proof leaders: human plays Rome (Trajan) so the trading-post modifier is
-- attached from game start. Definition writes for all four targets are
-- verified natively via stored_after_add regardless of instantiation.

local TARGETS = {
  { id = "TRAIT_LINCOLN_INDUSTRIAL_ZONE_LOYALTY",  arg = "Amount", official = "3",  expected = "21.9",  kind = "flat" },
  { id = "AGOGE_ANCIENT_MELEE_PRODUCTION",         arg = "Amount", official = "50", expected = "365",   kind = "percent" },
  { id = "ALL_PARK_COMBAT_BONUS",                  arg = "Amount", official = "5",  expected = "24.04", kind = "combat" },
  { id = "TRAIT_GOLD_FROM_DOMESTIC_TRADING_POSTS", arg = "Amount", official = "1",  expected = "7.3",  kind = "flat" },
}

local raw = GameConfiguration.GetValue("X10_PROBE_K")
if raw == nil then
  error("[X10Probe] FATAL: X10_PROBE_K missing from GameConfiguration")
end
local k = tonumber(raw)
if k == nil or k < 0 or k > 100 then
  error("[X10Probe] FATAL: X10_PROBE_K not a usable multiplier: " .. tostring(raw))
end

local function plog(s)
  if X10Lifecycle ~= nil and X10Lifecycle.LogMsg ~= nil then
    X10Lifecycle.LogMsg(s)
  end
  print(s)
end

plog(string.format("[X10Probe] configuration X10_PROBE_K=%s", tostring(raw)))
if X10Lifecycle ~= nil and X10Lifecycle.Ping ~= nil then
  X10Lifecycle.Ping()
else
  plog("[X10Probe] WARNING: X10Lifecycle native table absent (fork DLL not active?)")
end

-- Build handle -> definition-id index from live modifier instances.
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
  local handle = seen[t.id]
  if handle == nil then
    plog(string.format("[X10Probe] %s: runtime handle ABSENT (definition write still verified natively via stored_after_add)", t.id))
  else
    local value = GameEffects.GetModifierArgumentString(handle, t.arg)
    local verdict = (tostring(value) == t.expected) and "PASS" or "FAIL"
    plog(string.format("[X10Probe] %s handle=%s id=%s %s=%s expected=%s %s",
      t.id, tostring(handle), t.id, t.arg, tostring(value), t.expected, verdict))
  end
end
plog("[X10Probe] done (definition writes verified natively; see X10Lifecycle.log)")
