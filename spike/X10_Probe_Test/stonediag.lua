-- X10 Stonehenge ACTIVE-GAMEPLAY diagnostic (DISPOSABLE, local only).
-- Phase 3E final: placement-correct, two-phase across consecutive TurnBegins.
--
-- VERIFIED placement API (from official Firaxis scripts, not guessed):
--   Base\Assets\UI\WorldBuilderPlacement.lua (PlaceWonder):
--     ourPlot = Map.GetPlotByIndex( plot )
--     owner   = WorldBuilder.CityManager():GetPlotOwner( ourPlot )
--     city    = CityManager.GetCity(owner.PlayerID, owner.CityID)
--     bStatus, sStatus = WorldBuilder.CityManager():CreateBuilding(
--                           city, buildingEntry.Type.BuildingType, 100, plot )
--   -> 4th argument is the PLOT INDEX (the variable "plot" is the plot ID).
--   Base\Assets\UI\WorldBuilderPlayerEditor.lua uses the 3-arg form
--   (no placement), which is why Stonehenge (RequiresPlacement=true) was
--   rejected: the no-plot form cannot express a Wonder placement.
--   Base\Assets\UI\WorldBuilderPlotEditor.lua:
--     WorldBuilder.MapManager():SetTerrainType/SetFeatureType/SetImprovementType/
--       SetResourceType/CanPlaceResource (plot index form)
--     WorldBuilder.CityManager():SetPlotOwner( plot:GetX(), plot:GetY(),
--       playerID, cityID )  -- owned-plot control
--   Stonehenge requirements logged before the call:
--     RequiresPlacement, AdjacentResource (RESOURCE_STONE), flat land.
--
-- Plot preparation is PROBE-ONLY and fully logged: choose a deterministic
-- flat, land, unimproved plot near the capital, clear feature/improvement,
-- place RESOURCE_STONE on an adjacent plot, give the plot to the capital's
-- owner city. Random starting terrain is NOT relied upon.
--
-- Phase A: discovery + faith_before + plot prep + CreateBuilding(...plot)
--          + presence confirm + immediate yield as EVIDENCE ONLY.
-- Phase B (next TurnBegin): same city, Stonehenge present, helper live
--          handle, Amount ~= 14.6 (+-0.015), faith delta ~= 14.6 (+-0.05),
--          final PASS/FAIL. Failures latch (one-shot, no per-turn spam).
-- Nothing else changes between reads. Probe-only: prod DLL/registry/bridge
-- SQL/controller untouched.

local PHASE = 0  -- 0=waiting 1=awaiting B 2=done -1=latched failure
local PID, CID, FAITH_BEFORE = nil, nil, nil
local DISCOVERED = false
local PREP_LOGGED = false

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

local function dump_table(v)
  if v == nil then return "nil" end
  if type(v) ~= "table" then return tostring(v) end
  local parts = {}
  for k, val in pairs(v) do
    local ks = tostring(k)
    if type(val) == "table" then
      parts[#parts + 1] = ks .. "={" .. dump_table(val) .. "}"
    else
      parts[#parts + 1] = ks .. "=" .. tostring(val)
    end
  end
  table.sort(parts)
  return "{" .. table.concat(parts, ", ") .. "}"
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

local function terrain_name(idx)
  if idx == nil or idx < 0 then return "none" end
  local t = GameInfo.Terrains[idx]
  return t and t.TerrainType or tostring(idx)
end

local function feature_name(idx)
  if idx == nil or idx < 0 then return "none" end
  local f = GameInfo.Features[idx]
  return f and f.FeatureType or tostring(idx)
end

local function resource_name(idx)
  if idx == nil or idx < 0 then return "none" end
  local r = GameInfo.Resources[idx]
  return r and r.ResourceType or tostring(idx)
end

local function plot_info(plot)
  -- silent property readback for logging (no API-FAIL spam on optional reads)
  local function g(m)
    local ok, v = pcall(function() return plot[m](plot) end)
    if ok then return v end
    return nil
  end
  local x, _ = g("GetX")
  local y, _ = g("GetY")
  local idx, _ = g("GetIndex")
  local terr, _ = g("GetTerrainType")
  local feat, _ = g("GetFeatureType")
  local res, _ = g("GetResourceType")
  local imp, _ = g("GetImprovementType")
  local owner, _ = g("GetOwner")
  local hills = g("IsHills")
  local mtn = g("IsMountain")
  local water = g("IsWater")
  local owned = g("IsOwned")
  return {
    index = idx, x = x, y = y, owner = owner, terrain = terrain_name(terr),
    feature = feature_name(feat), resource = resource_name(res),
    improvement = imp, hills = hills, mountain = mtn, water = water,
    is_owned = owned,
  }
end

local function log_plot(tag, info)
  slog(string.format(
    "[X10StoneDiag] PLOT %s index=%s x/y=%s/%s owner=%s terrain=%s feature=%s resource=%s improvement=%s hills=%s mountain=%s water=%s owned=%s",
    tag, tostring(info.index), tostring(info.x), tostring(info.y), tostring(info.owner),
    tostring(info.terrain), tostring(info.feature), tostring(info.resource),
    tostring(info.improvement), tostring(info.hills), tostring(info.mountain),
    tostring(info.water), tostring(info.is_owned)))
end

-- Deterministic eligible-plot selection + probe-only preparation.
local function prepare_plot(pCity, pid, cid)
  local mm, okm = call(function() return WorldBuilder.MapManager() end, "MapManager()")
  if not okm or mm == nil then
    slog("[X10StoneDiag] LATCH-FAIL WorldBuilder.MapManager() unavailable")
    return nil
  end
  local cm, okc = call(function() return WorldBuilder.CityManager() end, "CityManager()")
  if not okc or cm == nil then
    slog("[X10StoneDiag] LATCH-FAIL WorldBuilder.CityManager() unavailable")
    return nil
  end

  local cx, okx = call(function() return pCity:GetX() end, "city:GetX")
  local cy, oky = call(function() return pCity:GetY() end, "city:GetY")
  if not okx or not oky or cx == nil or cy == nil then
    slog("[X10StoneDiag] LATCH-FAIL cannot read city coordinates")
    return nil
  end

  if not PREP_LOGGED then
    PREP_LOGGED = true
    local bi = GameInfo.Buildings["BUILDING_STONEHENGE"]
    slog(string.format(
      "[X10StoneDiag] REQUIREMENTS RequiresPlacement=%s AdjacentResource=%s MaxWorldInstances=%s",
      tostring(bi and bi.RequiresPlacement), tostring(bi and bi.AdjacentResource),
      tostring(bi and bi.MaxWorldInstances)))
  end

  local stoneIdx = GameInfo.Resources["RESOURCE_STONE"] and
    GameInfo.Resources["RESOURCE_STONE"].Index
  if stoneIdx == nil then
    slog("[X10StoneDiag] LATCH-FAIL RESOURCE_STONE not found in GameInfo")
    return nil
  end

  -- Deterministic nearest-first candidate order using the real Civ VI plot
  -- distance (Map.GetPlotDistance; verified from NaturalWonderGenerator.lua),
  -- radius 1 first, then 2, then 3. Only distances 1..3 are eligible.
  local cands = {}
  for dy = -3, 3 do
    for dx = -3, 3 do
      if dx ~= 0 or dy ~= 0 then
        local d, okd = call(function()
          return Map.GetPlotDistance(cx, cy, cx + dx, cy + dy)
        end, "GetPlotDistance")
        if okd and d ~= nil and d >= 1 and d <= 3 then
          cands[#cands + 1] = { x = cx + dx, y = cy + dy, d = d }
        end
      end
    end
  end
  table.sort(cands, function(a, b)
    if a.d ~= b.d then return a.d < b.d end
    if a.x ~= b.x then return a.x < b.x end
    return a.y < b.y
  end)

  -- Adjacent RESOURCE_STONE, established ONLY via readback evidence:
  -- reuse an existing stone plot, else place one on an eligible adjacent plot
  -- (CanPlaceResource first, matching WorldBuilderPlotEditor.lua) and verify.
  local function ensure_adjacent_stone(adj)
    local adjList, okadj = call(function() return adj end, "adjacent list")
    if not okadj or adjList == nil then return false end
    -- pass 1: reuse
    for i = 1, 6 do
      local p = adjList[i]
      if p ~= nil then
        local ai = plot_info(p)
        if ai.resource == "RESOURCE_STONE" then
          slog(string.format(
            "[X10StoneDiag] PREP adjacent stone REUSED index=%s x/y=%s/%s distance=1",
            tostring(ai.index), tostring(ai.x), tostring(ai.y)))
          return true
        end
      end
    end
    -- pass 2: place (each attempt verified by readback; keep trying others)
    for i = 1, 6 do
      local p = adjList[i]
      if p ~= nil then
        local ai = plot_info(p)
        if ai.water ~= true and ai.mountain ~= true and
           (ai.resource == nil or ai.resource == "none") then
          -- Firaxis plot-index form: CanPlaceResource(plotIndex, resourceIndex)
          -- (the local GameCore dispatches on argument count: a third arg would
          --  be parsed as the x/y/resource form). Two args only.
          local can, okcan = call(function()
            return WorldBuilder.MapManager():CanPlaceResource(ai.index, stoneIdx)
          end, "CanPlaceResource")
          if okcan and can == true then
            -- NOTE: call() returns (value, pcallOk); use the FIRST value.
            local res2 = call(function()
              return WorldBuilder.MapManager():SetResourceType(ai.index, stoneIdx, 1)
            end, "SetResourceType")
            local back = plot_info(p)
            slog(string.format(
              "[X10StoneDiag] PREP adjacent stone index=%s x/y=%s/%s -> set=%s readback=%s",
              tostring(ai.index), tostring(ai.x), tostring(ai.y),
              tostring(res2), tostring(back.resource)))
            if back.resource == "RESOURCE_STONE" then
              return true
            end
          else
            slog(string.format(
              "[X10StoneDiag] PREP adjacent stone NOT-PLACEABLE index=%s can=%s",
              tostring(ai.index), tostring(can)))
          end
        end
      end
    end
    return false
  end

  -- One candidate: mutation results are always confirmed by RE-READ.
  local function try_candidate(pos)
    local plot, okp = call(function() return Map.GetPlot(pos.x, pos.y) end,
                           "Map.GetPlot " .. pos.x .. "," .. pos.y)
    if not okp or plot == nil then return nil end
    local info = plot_info(plot)
    log_plot("candidate distance=" .. tostring(pos.d), info)

    if info.water == true or info.mountain == true then return nil end

    -- candidate resource: clear (probe-only) and verify
    if info.resource ~= nil and info.resource ~= "none" then
      local res = call(function()
        return WorldBuilder.MapManager():SetResourceType(info.index, -1)
      end, "SetResourceType-clear")
      local back = plot_info(plot)
      slog(string.format(
        "[X10StoneDiag] PREP clear resource index=%s (%s) -> set=%s readback=%s",
        tostring(info.index), tostring(info.resource), tostring(res),
        tostring(back.resource)))
      if back.resource ~= nil and back.resource ~= "none" then
        slog("[X10StoneDiag] candidate rejected: resource not cleared")
        return nil
      end
    end

    -- candidate improvement: clear and verify
    if info.improvement ~= nil and info.improvement ~= -1 then
      local res = call(function()
        return WorldBuilder.MapManager():SetImprovementType(info.index, -1)
      end, "SetImprovementType")
      local back = plot_info(plot)
      slog(string.format(
        "[X10StoneDiag] PREP clear improvement index=%s -> set=%s readback=%s",
        tostring(info.index), tostring(res), tostring(back.improvement)))
      if back.improvement ~= nil and back.improvement ~= -1 then
        slog("[X10StoneDiag] candidate rejected: improvement not cleared")
        return nil
      end
    end

    -- candidate feature: clear and verify
    if info.feature ~= nil and info.feature ~= "none" then
      local res = call(function()
        return WorldBuilder.MapManager():SetFeatureType(info.index, -1)
      end, "SetFeatureType")
      local back = plot_info(plot)
      slog(string.format(
        "[X10StoneDiag] PREP clear feature index=%s (%s) -> set=%s readback=%s",
        tostring(info.index), tostring(info.feature), tostring(res),
        tostring(back.feature)))
      if back.feature ~= nil and back.feature ~= "none" then
        slog("[X10StoneDiag] candidate rejected: feature not cleared")
        return nil
      end
    end

    -- Final plot shape check (land / not mountain / not hills).
    local shape = plot_info(plot)
    if shape.water == true or shape.mountain == true or shape.hills == true then
      slog("[X10StoneDiag] candidate rejected: not flat land")
      return nil
    end

    -- Adjacent stone via readback evidence only.
    local adj, okadj = call(function()
      return Map.GetAdjacentPlots(info.x, info.y)
    end, "GetAdjacentPlots")
    local stone_ok = false
    if okadj and adj ~= nil then
      stone_ok = ensure_adjacent_stone(adj)
    end
    if not stone_ok then
      slog("[X10StoneDiag] candidate rejected: no adjacent RESOURCE_STONE verified")
      return nil
    end

    -- Ownership: assign the plot to the capital's owner city, then verify.
    local res3 = call(function()
      return WorldBuilder.CityManager():SetPlotOwner(info.x, info.y, pid, cid)
    end, "SetPlotOwner")
    local owned = plot_info(plot)
    local owned_ok = (owned.is_owned == true) and
      (owned.owner == pid)
    -- Same manager the verified Wonder path uses: GetPlotOwner(plot). The
    -- returned shape is logged verbatim and, when it exposes both fields,
    -- PlayerID/CityID are also verified. Structure mismatch alone is NOT a
    -- rejection (robustness only).
    local ownerTbl, oko = call(function()
      return WorldBuilder.CityManager():GetPlotOwner(info.index)
    end, "GetPlotOwner")
    local op_pid, op_cid = nil, nil
    if type(ownerTbl) == "table" then
      op_pid = ownerTbl.PlayerID
      op_cid = ownerTbl.CityID
    end
    local owners_match = (type(ownerTbl) == "table") and
      (op_pid == pid) and (op_cid == cid)
    if type(ownerTbl) ~= "table" then
      slog(string.format(
        "[X10StoneDiag] PREP GetPlotOwner returned non-table (%s); not treated as a rejection",
        tostring(ownerTbl)))
    end
    slog(string.format(
      "[X10StoneDiag] PREP owner set x/y=%s/%s pid=%s cid=%s -> set=%s readback_owner=%s owned=%s getplotowner_player=%s getplotowner_city=%s owners_match=%s",
      tostring(info.x), tostring(info.y), tostring(pid), tostring(cid), tostring(res3),
      tostring(owned.owner), tostring(owned.is_owned),
      tostring(op_pid), tostring(op_cid), tostring(owners_match)))
    if not owned_ok then
      slog("[X10StoneDiag] candidate rejected: ownership not verified")
      return nil
    end

    -- Authoritative PREFLIGHT: every condition must be true, from readback.
    local pre = plot_info(plot)
    local flat = (pre.hills ~= true and pre.mountain ~= true)
    local land = (pre.water ~= true)
    local feature_none = (pre.feature == nil or pre.feature == "none")
    local imp_none = (pre.improvement == nil or pre.improvement == -1)
    local res_none = (pre.resource == nil or pre.resource == "none")
    local d_ok = (pos.d >= 1 and pos.d <= 3)
    slog(string.format(
      "[X10StoneDiag] PREFLIGHT plot=%s distance=%s owner=%s owned_by_capital=%s getplotowner_player=%s getplotowner_city=%s owners_match=%s flat=%s land=%s feature=%s improvement=%s resource=%s adjacent_stone=%s",
      tostring(pre.index), tostring(pos.d), tostring(pre.owner), tostring(owned_ok),
      tostring(op_pid), tostring(op_cid), tostring(owners_match),
      tostring(flat), tostring(land), tostring(pre.feature), tostring(pre.improvement),
      tostring(pre.resource), tostring(stone_ok)))
    if owned_ok and flat and land and feature_none and imp_none and res_none
       and stone_ok and d_ok then
      log_plot("selected distance=" .. tostring(pos.d), pre)
      return pre.index
    end
    slog("[X10StoneDiag] candidate rejected: preflight conditions not all true")
    return nil
  end

  for _, pos in ipairs(cands) do
    local r = try_candidate(pos)
    if r ~= nil then return r end
  end
  slog("[X10StoneDiag] LATCH-FAIL no eligible placement plot found near capital")
  return nil
end

-- Prerequisite technology, granted through the verified WorldBuilder player
-- API (official evidence, WorldBuilderPlayerEditor.lua):
--   OnTechSelected: local progress = selected and 100 or -1;
--     WorldBuilder.PlayerManager():SetPlayerHasTech(playerIdx, techIdx, progress)
--   OnPlayerTechEdited: WorldBuilder.PlayerManager():PlayerHasTech(player, tech)
-- So: grant = SetPlayerHasTech(pid, techIndex, 100); readback = PlayerHasTech.
-- The prerequisite is resolved dynamically from the Buildings row.
local function ensure_prereq_tech(pid)
  local pm, okpm = call(function() return WorldBuilder.PlayerManager() end,
                        "PlayerManager()")
  if not okpm or pm == nil then
    slog("[X10StoneDiag] LATCH-INCONCLUSIVE WorldBuilder.PlayerManager() unavailable")
    return false
  end
  if pm.SetPlayerHasTech == nil then
    slog("[X10StoneDiag] LATCH-INCONCLUSIVE SetPlayerHasTech unavailable")
    return false
  end
  local bi = GameInfo.Buildings["BUILDING_STONEHENGE"]
  local prereqName = bi and bi.PrereqTech
  if prereqName == nil or prereqName == "" or prereqName == "NONE" then
    slog("[X10StoneDiag] TECH prerequisite=NONE (nothing to grant)")
    return true
  end
  local techRow = GameInfo.Technologies[prereqName]
  local techIdx = techRow and techRow.Index
  slog(string.format("[X10StoneDiag] TECH prerequisite=%s", tostring(prereqName)))
  slog(string.format("[X10StoneDiag] tech_index=%s", tostring(techIdx)))
  if techIdx == nil then
    slog("[X10StoneDiag] LATCH-INCONCLUSIVE prerequisite tech row not found")
    return false
  end
  local had_before, okb = call(function()
    return pm:PlayerHasTech(pid, techIdx)
  end, "PlayerHasTech-before")
  slog(string.format("[X10StoneDiag] had_before=%s", tostring(had_before)))
  if okb and had_before == true then
    slog("[X10StoneDiag] grant_result=already-owned")
    slog(string.format("[X10StoneDiag] has_after=%s", "true"))
    return true
  end
  local grantRes = call(function()
    return pm:SetPlayerHasTech(pid, techIdx, 100)
  end, "SetPlayerHasTech")
  local has_after, oka = call(function()
    return pm:PlayerHasTech(pid, techIdx)
  end, "PlayerHasTech-after")
  slog(string.format("[X10StoneDiag] grant_result=%s", tostring(grantRes)))
  slog(string.format("[X10StoneDiag] has_after=%s", tostring(has_after)))
  if has_after ~= true then
    slog("[X10StoneDiag] LATCH-INCONCLUSIVE prerequisite tech not owned after grant")
    return false
  end
  return true
end

local function phase_a()
  local pCity, pid = find_city()
  if pCity == nil then
    if PHASE == 0 then slog("[X10StoneDiag] WAIT no city yet (settle first)") end
    return
  end
  local cid, okcid = call(function() return pCity:GetID() end, "GetID")
  if not okcid or cid == nil then
    slog("[X10StoneDiag] WAIT cannot read city ID; retry next turn")
    return
  end
  local k = tonumber(GameConfiguration.GetValue("X10_MULTIPLIER")) or 0
  local expected = 2 * k
  local fIdx = GameInfo.Yields["YIELD_FAITH"].Index
  local cname = tostring(pCity:GetName())

  local wb = WorldBuilder
  if type(wb) ~= "table" or wb.CityManager == nil then
    slog("[X10StoneDiag] LATCH-FAIL WorldBuilder.CityManager unavailable")
    PHASE = -1
    return
  end
  local cm, cmok = call(function() return wb.CityManager() end, "CityManager()")
  if not cmok or cm == nil or cm.CreateBuilding == nil then
    slog("[X10StoneDiag] LATCH-FAIL WorldBuilder.CityManager():CreateBuilding unavailable")
    PHASE = -1
    return
  end

  if not DISCOVERED then
    DISCOVERED = true
    local b, q
    call(function() b = pCity:GetBuildings() end, "GetBuildings")
    call(function() q = pCity:GetBuildQueue() end, "GetBuildQueue")
    slog(string.format(
      "[X10StoneDiag] DISCOVERY CityManager.CreateBuilding=%s MapManager=%s city.GetBuildings=%s city.GetBuildQueue=%s bldg.CreateBuilding=%s queue.CreateBuilding=%s queue.AddToQueue=%s",
      tostring(cm.CreateBuilding ~= nil),
      tostring(type(wb.MapManager)),
      tostring(type(pCity.GetBuildings)),
      tostring(type(pCity.GetBuildQueue)),
      b and (b.CreateBuilding ~= nil and "function" or "absent") or "n/a",
      q and (q.CreateBuilding ~= nil and "function" or "absent") or "n/a",
      q and (q.AddToQueue ~= nil and "function" or "absent") or "n/a"))
  end

  local bIdx = GameInfo.Buildings["BUILDING_STONEHENGE"].Index
  local bld = pCity:GetBuildings()
  local before, okb = call(function() return pCity:GetYield(fIdx) end, "GetYield-before")
  local had, okh = call(function() return bld:HasBuilding(bIdx) end, "HasBuilding-before")
  if before == nil then before = 0 end
  if had == nil then had = false end
  slog(string.format(
    "[X10StoneDiag] PHASE-A city=%s city_id=%d faith_before=%.4f stonehenge_present_before=%s k=%.7f expected_delta=%.4f",
    cname, cid, before, tostring(had), k, expected))

  if not had then
    -- Prerequisite technology must exist before CreateBuilding: the live
    -- run proved Stonehenge is otherwise rejected with MeetsRequirements=
    -- false / NeededTech. Grant + readback first; inconclusive tech state
    -- latches without touching placement or calling CreateBuilding.
    if not ensure_prereq_tech(pid) then
      slog("[X10StoneDiag] LATCH-INCONCLUSIVE prerequisite tech unavailable; not calling CreateBuilding")
      PHASE = -1
      return
    end
    -- Stonehenge is a placed Wonder: the 4th CreateBuilding argument is the
    -- plot index, so a valid placement plot must be prepared first.
    local plotIdx = prepare_plot(pCity, pid, cid)
    if plotIdx == nil then
      slog("[X10StoneDiag] LATCH-FAIL no placement plot; not retrying")
      PHASE = -1
      return
    end
    local statusStr, stok = "", false
    statusStr, stok = call(function()
      local s, t = cm:CreateBuilding(pCity, "BUILDING_STONEHENGE", 100, plotIdx)
      return tostring(s) .. " status=" .. dump_table(t)
    end, "CreateBuilding-Stonehenge")
    if not stok then
      slog("[X10StoneDiag] LATCH-FAIL CreateBuilding raised; not retrying")
      PHASE = -1
      return
    end
    local has, okh2 = call(function() return bld:HasBuilding(bIdx) end,
                          "HasBuilding-confirm")
    if has == nil then has = false end
    slog(string.format("[X10StoneDiag] CreateBuilding(plot=%s) result=%s present=%s",
      tostring(plotIdx), statusStr, tostring(has)))
    slog(string.format("[X10StoneDiag] %s", has and "CREATE_OK" or "CREATE_FAILED"))
    if not has then
      slog("[X10StoneDiag] LATCH-FAIL Stonehenge not present after CreateBuilding; not retrying")
      PHASE = -1
      return
    end
  else
    slog("[X10StoneDiag] NOTE Stonehenge already present; delta still measured but attribution is weaker")
  end

  -- evidence only: immediate yield may lag; verdict is Phase B.
  local imm, oki = call(function() return pCity:GetYield(fIdx) end, "GetYield-immediate")
  if imm == nil then imm = before end
  local amt, h = helper_amount()
  slog(string.format(
    "[X10StoneDiag] PHASE-A city_id=%d faith_immediate_after_create=%.4f helper_handle=%s helper_amount=%s (evidence only; verdict next turn)",
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
    slog(string.format(
      "[X10StoneDiag] WAIT city changed (want pid=%s cid=%s); holding Phase B",
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
  slog(string.format(
    "[X10StoneDiag] PHASE-B city=%s city_id=%d faith_before=%.4f faith_next_turn=%.4f stonehenge_present=%s helper_handle=%s helper_amount=%s delta=%.4f expected=%.4f",
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
