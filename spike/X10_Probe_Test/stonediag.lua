-- X10 Stonehenge ACTIVE-GAMEPLAY diagnostic (DISPOSABLE, local only).
-- Phase 3E (hardened): two-phase across consecutive TurnBegins so the yield
-- delta never depends on synchronous City yield-cache refresh after
-- CityBuildings:CreateBuilding.
--
-- Phase A (first TurnBegin with a city):
--   record faith_before, CreateBuilding(Stonehenge), confirm presence,
--   record helper-handle appearance, log CREATE_OK / API_FAIL.
--   An immediate post-create read is logged as evidence only, never judged.
-- Phase B (next TurnBegin):
--   confirm same city + Stonehenge, read faith_next_turn, rescan helper,
--   assert Amount ~= 14.6 (+-0.015) and delta ~= 14.6 (+-0.05), emit PASS/FAIL.
--
-- Nothing else is touched between the reads (no tiles, policies, pantheons,
-- population). Never shipped; registry/DLL untouched.

local PHASE = 0  -- 0 = waiting for city, 1 = created, awaiting next turn
local PID = nil
local CID = nil
local FAITH_BEFORE = nil

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

local function find_city()
  local pid, ok = call(function() return Game.GetLocalPlayer() end, "GetLocalPlayer")
  if not ok or pid == nil or pid < 0 then pid = 0 end
  local pPlayer = Players[pid]
  if pPlayer == nil then return nil, nil end
  local pCities, okc = call(function() return pPlayer:GetCities() end, "GetCities")
  if not okc or pCities == nil then return nil, nil end
  local pCity, okcap = call(function() return pCities:GetCapitalCity() end, "GetCapitalCity")
  if (not okcap) or pCity == nil then
    local mem, okm = call(function() return pCities:Members() end, "Members")
    if okm and mem ~= nil then
      for c in mem do pCity = c; break end
    end
  end
  return pCity, pid
end

local function helper_amount()
  local handles, okg = call(function() return GameEffects.GetModifiers() end, "GetModifiers")
  if not okg or handles == nil then return nil, nil end
  for _, h in pairs(handles) do
    local d = GameEffects.GetModifierDefinition(h)
    local did = (d ~= nil) and (d.Id or d.ModifierId or d.id) or nil
    if did == "X10_STONEHENGE_YIELD_FAITH" then
      local v = GameEffects.GetModifierArgumentString(h, "Amount")
      return tonumber(v), h
    end
  end
  return nil, nil
end

local function phase_a()
  local pCity, pid = find_city()
  if pCity == nil then
    slog("[X10StoneDiag] WAIT no city yet (settle first)")
    return
  end
  local k = tonumber(GameConfiguration.GetValue("X10_MULTIPLIER")) or 0
  local expected = 2 * k  -- audited Stonehenge direct faith 2, scaled by k
  local bIdx = GameInfo.Buildings["BUILDING_STONEHENGE"].Index
  local fIdx = GameInfo.Yields["YIELD_FAITH"].Index
  local cid, okcid = call(function() return pCity:GetID() end, "GetID")
  if not okcid or cid == nil then
    slog("[X10StoneDiag] API-FAIL cannot read city ID; retry next turn")
    return
  end
  local cname = tostring(pCity:GetName())
  local bld = pCity:GetBuildings()
  local before, okb = call(function() return pCity:GetYield(fIdx) end, "GetYield-before")
  local had, okh = call(function() return bld:HasBuilding(bIdx) end, "HasBuilding-before")
  if before == nil then before = 0 end
  if had == nil then had = false end
  slog(string.format("[X10StoneDiag] PHASE-A city=%s city_id=%d faith_before=%.4f stonehenge_present_before=%s k=%.7f expected_delta=%.4f",
    cname, cid, before, tostring(had), k, expected))

  local created = had
  if not had then
    local _, okc2 = call(function() bld:CreateBuilding(bIdx) end, "CreateBuilding-Stonehenge")
    if not okc2 then
      slog("[X10StoneDiag] API-FAIL cannot instantiate Stonehenge via CityBuildings:CreateBuilding")
      return
    end
    local has, okh2 = call(function() return bld:HasBuilding(bIdx) end, "HasBuilding-confirm")
    if has == nil then has = false end
    created = has
    slog(string.format("[X10StoneDiag] %s stonehenge_present_after_create=%s",
      has and "CREATE_OK" or "API-FAIL", tostring(has)))
    if not has then return end  -- retry Phase A next turn
  else
    slog("[X10StoneDiag] NOTE Stonehenge already present; delta still measured but attribution is weaker")
  end

  -- Immediate read: evidence only, never judged (yield cache may lag).
  local imm, oki = call(function() return pCity:GetYield(fIdx) end, "GetYield-immediate")
  if imm == nil then imm = before end
  local amt, h = helper_amount()
  slog(string.format("[X10StoneDiag] PHASE-A city_id=%d faith_immediate_after_create=%.4f helper_handle=%s helper_amount=%s (evidence only; verdict next turn)",
    cid, imm, tostring(h), tostring(amt)))

  PID, CID, FAITH_BEFORE, PHASE = pid, cid, before, 1
end

local function phase_b()
  local pCity, pid = find_city()
  if pCity == nil then
    slog("[X10StoneDiag] WAIT city vanished; holding Phase B")
    return
  end
  local cid, okcid = call(function() return pCity:GetID() end, "GetID recheck")
  if not okcid or cid == nil or cid ~= CID or pid ~= PID then
    slog(string.format("[X10StoneDiag] WAIT city changed (want pid=%s cid=%s); holding Phase B",
      tostring(PID), tostring(CID)))
    return
  end
  local cname = tostring(pCity:GetName())
  local bIdx = GameInfo.Buildings["BUILDING_STONEHENGE"].Index
  local fIdx = GameInfo.Yields["YIELD_FAITH"].Index
  local k = tonumber(GameConfiguration.GetValue("X10_MULTIPLIER")) or 0
  local expected = 2 * k
  local bld = pCity:GetBuildings()
  local has, okh = call(function() return bld:HasBuilding(bIdx) end, "HasBuilding-phaseB")
  if has == nil then has = false end
  local after, oka = call(function() return pCity:GetYield(fIdx) end, "GetYield-next-turn")
  if after == nil then after = FAITH_BEFORE end
  local amt, h = helper_amount()
  local delta = after - FAITH_BEFORE
  slog(string.format("[X10StoneDiag] PHASE-B city=%s city_id=%d faith_before=%.4f faith_next_turn=%.4f stonehenge_present=%s helper_handle=%s helper_amount=%s delta=%.4f expected=%.4f",
    cname, cid, FAITH_BEFORE, after, tostring(has), tostring(h), tostring(amt), delta, expected))
  local pass = has and (amt ~= nil)
    and (math.abs(amt - expected) < 0.015)
    and (math.abs(delta - expected) < 0.05)
  slog(string.format("[X10StoneDiag] FINAL city_id=%d => %s",
    cid, pass and "PASS" or "FAIL"))
  PHASE = 2
end

local function on_turn()
  if PHASE == 0 then
    pcall(phase_a)
  elseif PHASE == 1 then
    pcall(phase_b)
  end
end

pcall(on_turn)
if Events ~= nil and Events.TurnBegin ~= nil then
  Events.TurnBegin.Add(function() pcall(on_turn) end)
else
  slog("[X10StoneDiag] API-FAIL no Events.TurnBegin")
end
