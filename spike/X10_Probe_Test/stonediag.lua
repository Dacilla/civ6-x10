-- X10 Stonehenge ACTIVE-GAMEPLAY diagnostic (DISPOSABLE, local only).
-- Phase 3E: proves the generated bridge helper X10_STONEHENGE_YIELD_FAITH
-- contributes its transformed Amount to a CONSTRUCTED wonder's city yield.
-- Phase 3D already proved definition-store persistence; this observes the
-- live gameplay result via before/after city-yield delta plus the active
-- runtime modifier handle. Never shipped; registry/DLL untouched.
--
-- Mechanism (all standard Civ VI gameplay Lua, no memory/DB tricks):
--   TurnBegin hook (deferred until the local player's first city exists)
--   CityBuildings:CreateBuilding  (placement requirements bypassed on purpose)
--   City:GetYield(YIELD_FAITH)     (before/after delta isolates Stonehenge)
--   GameEffects.GetModifiers scan (helper active + Amount readback)

local DONE = false

local function slog(s)
  if X10Lifecycle ~= nil and X10Lifecycle.LogMsg ~= nil then
    X10Lifecycle.LogMsg(s)
  end
  print(s)
end

local function call(fn, what)
  local ok, res = pcall(fn)
  if not ok then
    slog(string.format("[X10StoneDiag] API-FAIL %s: %s", what, tostring(res)))
    return nil, false
  end
  return res, true
end

local function run_once()
  if DONE then return end
  local pid, ok = call(function() return Game.GetLocalPlayer() end, "GetLocalPlayer")
  if not ok or pid == nil or pid < 0 then pid = 0 end
  local pPlayer = Players[pid]
  if pPlayer == nil then
    slog("[X10StoneDiag] WAIT no player object yet")
    return
  end
  local pCities, okc = call(function() return pPlayer:GetCities() end, "GetCities")
  if not okc or pCities == nil then return end
  local pCity, okcap = call(function() return pCities:GetCapitalCity() end, "GetCapitalCity")
  if (not okcap) or pCity == nil then
    local mem, okm = call(function() return pCities:Members() end, "Members")
    if okm and mem ~= nil then
      for c in mem do pCity = c; break end
    end
  end
  if pCity == nil then
    slog("[X10StoneDiag] WAIT no city yet (settle first)")
    return
  end
  DONE = true

  local k = tonumber(GameConfiguration.GetValue("X10_MULTIPLIER")) or 0
  local expected = 2 * k  -- audited Stonehenge direct faith 2, scaled by k

  local bIdx = GameInfo.Buildings["BUILDING_STONEHENGE"].Index
  local fIdx = GameInfo.Yields["YIELD_FAITH"].Index
  local cname = tostring(pCity:GetName())

  local bld = pCity:GetBuildings()
  local before, okb = call(function() return pCity:GetYield(fIdx) end, "GetYield-before")
  local had, okh = call(function() return bld:HasBuilding(bIdx) end, "HasBuilding-before")
  if before == nil then before = 0 end
  if had == nil then had = false end
  slog(string.format("[X10StoneDiag] city=%s faith_before=%.4f stonehenge_present_before=%s k=%.7f expected_delta=%.4f",
    cname, before, tostring(had), k, expected))

  if not had then
    local _, okc2 = call(function() bld:CreateBuilding(bIdx) end, "CreateBuilding-Stonehenge")
    if not okc2 then
      slog("[X10StoneDiag] FAIL cannot instantiate Stonehenge via CityBuildings:CreateBuilding")
      return
    end
  else
    slog("[X10StoneDiag] NOTE Stonehenge already present; delta still measured but attribution is weaker")
  end

  local after, oka = call(function() return pCity:GetYield(fIdx) end, "GetYield-after")
  local has, okh2 = call(function() return bld:HasBuilding(bIdx) end, "HasBuilding-after")
  if after == nil then after = 0 end
  if has == nil then has = false end
  local delta = after - before
  slog(string.format("[X10StoneDiag] city=%s faith_after=%.4f stonehenge_present_after=%s delta=%.4f",
    cname, after, tostring(has), delta))

  -- Active runtime handle for the generated helper (absent before the
  -- building exists; present + scaled once its building is constructed).
  local amt = nil
  local handles, okg = call(function() return GameEffects.GetModifiers() end, "GetModifiers")
  if okg and handles ~= nil then
    for _, h in pairs(handles) do
      local d = GameEffects.GetModifierDefinition(h)
      local did = (d ~= nil) and (d.Id or d.ModifierId or d.id) or nil
      if did == "X10_STONEHENGE_YIELD_FAITH" then
        local v = GameEffects.GetModifierArgumentString(h, "Amount")
        amt = tonumber(v)
        slog(string.format("[X10StoneDiag] helper handle=%s Amount=%s", tostring(h), tostring(v)))
        break
      end
    end
  end
  if amt == nil then
    slog("[X10StoneDiag] helper X10_STONEHENGE_YIELD_FAITH runtime handle ABSENT")
  end

  local pass = has and (amt ~= nil)
    and (math.abs(amt - expected) < 0.015)
    and (math.abs(delta - expected) < 0.05)
  slog(string.format("[X10StoneDiag] expected=%.4f observed_delta=%.4f helper_amount=%s => %s",
    expected, delta, tostring(amt), pass and "PASS" or "FAIL"))
end

-- Attempt immediately (covers loading into an existing city), then defer to
-- turn starts until the first city exists.
pcall(run_once)
if Events ~= nil and Events.TurnBegin ~= nil then
  Events.TurnBegin.Add(function() pcall(run_once) end)
else
  slog("[X10StoneDiag] API-FAIL no Events.TurnBegin")
end
