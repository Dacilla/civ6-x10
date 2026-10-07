-- X10 CE spike probe (DISPOSABLE, read-only).
-- Pipeline under test: GameConfiguration -> Lua transform -> GameEffects read.
-- The WRITE step (CE ModifierDefinitions.SetArgument) does not exist yet;
-- this probe validates everything up to the write and logs exact expectations.
-- Expected values at k=7.3 (from audit official DB):
--   A flat:    TRAIT_LINCOLN_INDUSTRIAL_ZONE_LOYALTY/Amount 3    -> 21.9
--   B percent: AGOGE_ANCIENT_MELEE_PRODUCTION/Amount 50          -> 365
--   C combat:  ALL_PARK_COMBAT_BONUS/Amount 5                    -> 24.04

local PROBES = {
  { id = "TRAIT_LINCOLN_INDUSTRIAL_ZONE_LOYALTY", arg = "Amount", kind = "flat" },
  { id = "AGOGE_ANCIENT_MELEE_PRODUCTION",        arg = "Amount", kind = "percent" },
  { id = "ALL_PARK_COMBAT_BONUS",                 arg = "Amount", kind = "combat" },
}

local function getK()
  local ok, v = pcall(function() return GameConfiguration.GetValue("X10_PROBE_K") end)
  if ok and type(v) == "number" and v >= 0 and v <= 100 then return v end
  return 7.3
end

local function x10(kind, v, k)
  if kind == "combat" then
    return 25 * math.log(k * (math.exp(v / 25) - 1) + 1)
  elseif kind == "probability" then
    return 1 - (1 - v) ^ k
  elseif kind == "discount" then
    return (1 - (1 - math.abs(v)) ^ k) * (v < 0 and -1 or 1)
  else
    return v * k
  end
end

function OnTurnBegin()
  local k = getK()
  print(string.format("[X10Probe] k=%s", tostring(k)))
  for _, p in ipairs(PROBES) do
    local official = GameEffects.GetModifierArgumentString(p.id, p.arg)
    local v = tonumber(official)
    if v == nil then
      print(string.format("[X10Probe] %s/%s official=%s (non-numeric, skip)",
        p.id, p.arg, tostring(official)))
    else
      local scaled = x10(p.kind, v, k)
      print(string.format("[X10Probe] %s/%s official=%s scaled=%.2f kind=%s",
        p.id, p.arg, tostring(official), scaled, p.kind))
      -- WRITE STEP (blocked on CE extension, logged not executed):
      -- ModifierDefinitions.SetArgument(p.id, p.arg, scaled)
    end
  end
end
Events.PlayerTurnInitialized.Add(OnTurnBegin);
print("[X10Probe] loaded (read-only)");
