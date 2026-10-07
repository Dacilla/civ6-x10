-- X10 native probe (DISPOSABLE). Fails loudly; no silent fallback.
-- Expected at k=7.3 (official baseline):
--   TRAIT_LINCOLN_INDUSTRIAL_ZONE_LOYALTY/Amount 3 -> 21.9
--   AGOGE_ANCIENT_MELEE_PRODUCTION/Amount 50       -> 365
--   ALL_PARK_COMBAT_BONUS/Amount 5                 -> 24.04

local PROBES = {
  { id = "TRAIT_LINCOLN_INDUSTRIAL_ZONE_LOYALTY", arg = "Amount", kind = "flat" },
  { id = "AGOGE_ANCIENT_MELEE_PRODUCTION",        arg = "Amount", kind = "percent" },
  { id = "ALL_PARK_COMBAT_BONUS",                 arg = "Amount", kind = "combat" },
}

local raw = GameConfiguration.GetValue("X10_PROBE_K")
if raw == nil then
  error("[X10Probe] FATAL: X10_PROBE_K missing from GameConfiguration")
end
local k = tonumber(raw)
if k == nil or k < 0 or k > 100 then
  error("[X10Probe] FATAL: X10_PROBE_K not a usable multiplier: " .. tostring(raw))
end
print(string.format("[X10Probe] configuration X10_PROBE_K=%s", tostring(raw)))

local function x10(kind, v, kk)
  if kind == "combat" then
    return 25 * math.log(kk * (math.exp(v / 25) - 1) + 1)
  else
    return v * kk
  end
end

if X10Lifecycle ~= nil and X10Lifecycle.Ping ~= nil then
  X10Lifecycle.Ping()
else
  print("[X10Probe] WARNING: X10Lifecycle native table absent (fork DLL not active?)")
end

for _, p in ipairs(PROBES) do
  local official = GameEffects.GetModifierArgumentString(p.id, p.arg)
  local v = tonumber(official)
  if v == nil then
    print(string.format("[X10Probe] %s/%s official=%s (non-numeric, skip)",
      p.id, p.arg, tostring(official)))
  else
    print(string.format("[X10Probe] %s/%s official=%s scaled=%.2f kind=%s",
      p.id, p.arg, tostring(official), x10(p.kind, v, k), p.kind))
  end
end
print("[X10Probe] done (read-only; no writes attempted)")
