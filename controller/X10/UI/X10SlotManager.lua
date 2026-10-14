-- X10SlotManager.lua
-- On-demand Reserve Policy unlocker (Phase 8B.4 source-driven 8B.4.4).
--
-- Runs as a gameplay script (AddGameplayScripts, simulation context --
-- the Wonder-x10 precedent). The 700 Reserve policies ship DORMANT
-- (ExplicitUnlock, no civic). This manager unlocks source-driven
-- TARGET counts: for each active audited +1 slot source, (k - 1)
-- Reserves of the source's slot type at integral armed k. Ordinary
-- Code of Laws: zero active sources, zero visible.
--
-- Replaces the 8B.4 gameplay-side legality matcher (REMOVED 8B.4.4):
-- Lua.log proved CanSlotPolicy is unavailable in this execution
-- context, so engine matching here could never work -- while native
-- REPEAT multiplication itself works. Targets derive from sources,
-- never from slot enumeration.
--
-- Safety properties (all load-bearing, all human-gated in P0C):
--   * every engine call is pcall-guarded; unresolvable configuration,
--     missing enumeration, or missing unlock APIs abort loudly with
--     zero unlocks (fail closed);
--   * idempotent: toUnlock = target - alreadyUnlocked; satisfied
--     targets reconcile silently to 0;
--   * bounded over-supply only (never under-supply): real policies are
--     NOT subtracted; second sources accumulate;
--   * human majors only; bounded event set (init, LoadScreenClose,
--     WonderCompleted, TurnBegin) -- no per-AI-turn hooks, no log spam:
--     lines only for source activation, targets, actual unlocks,
--     warnings/errors;
--   * one-way UnlockPolicy is acceptable because every source is
--     permanent once active (wonder built, leader/civ fixed at setup).
--     Exception: a lost wonder city leaves its fillers unlocked
--     (bounded over-supply, still slottable nowhere harmful).
-- No auto-slotting ships here: slotting stays manual until a runtime-
-- proven pass enables it (see docs/PHASE_8B.md section 9).

local FILLER_MATCH = "POLICY_X10_FILLER_";

-- Authoritative seven +1 slot sources. Mirrors
-- civ6x10.eight_b.SLOT_BASES (base, slot, kind, attach id, module);
-- tests/test_phase8b4_ux_compat.py pins parity -- never a second
-- guessed list.
local SOURCES = {
  { base = "POTALA_PALACE_DIPLOMATIC_GOVERNMENT_SLOT",
    slot = "SLOT_DIPLOMATIC", kind = "building",
    id = "BUILDING_POTALA_PALACE", module = "wonders" },
  { base = "FORBIDDEN_CITY_WILDCARD_GOVERNMENT_SLOT",
    slot = "SLOT_WILDCARD", kind = "building",
    id = "BUILDING_FORBIDDEN_CITY", module = "wonders" },
  { base = "ALHAMBRA_MILITARY_GOVERNMENT_SLOT",
    slot = "SLOT_MILITARY", kind = "building",
    id = "BUILDING_ALHAMBRA", module = "wonders" },
  { base = "BIG_BEN_ECONOMIC_GOVERNMENT_SLOT",
    slot = "SLOT_ECONOMIC", kind = "building",
    id = "BUILDING_BIG_BEN", module = "wonders" },
  { base = "TRAIT_ECONOMIC_GOVERNMENT_SLOT",
    slot = "SLOT_ECONOMIC", kind = "trait",
    id = "TRAIT_LEADER_KUBLAI", module = "traits" },
  { base = "TRAIT_MILITARY_GOVERNMENT_SLOT",
    slot = "SLOT_MILITARY", kind = "trait",
    id = "TRAIT_LEADER_HOLY_ROMAN_EMPEROR", module = "traits" },
  { base = "TRAIT_WILDCARD_GOVERNMENT_SLOT",
    slot = "SLOT_WILDCARD", kind = "trait",
    id = "TRAIT_CIVILIZATION_PLATOS_REPUBLIC", module = "traits" },
};

local MODULE_BITS = { wonders = 16, traits = 1 };
local MODULE_PARAM_IDS = { wonders = "X10ModuleWonders",
                           traits = "X10ModuleTraits" };
local MODULE_CONFIG_IDS = { wonders = "X10_MODULE_WONDERS",
                            traits = "X10_MODULE_TRAITS" };

local function x10log(msg)
  print("[X10SlotManager] " .. tostring(msg));
end

-- pcall wrapper returning (ok, first_result). Never throws.
local function Try(fn)
  local ok, r = pcall(fn);
  if ok then return true, r; end
  return false, nil;
end

local function IsOurs(policyType)
  return policyType ~= nil
    and string.find(policyType, FILLER_MATCH, 1, true) ~= nil;
end

-- Human major candidates. Primary: PlayerManager.GetAliveMajorIDs
-- (documented number[] API); second: GetAliveMajors Player objects via
-- GetID; last: bounded 0..63 index scan. Each stage runs only if the
-- previous yielded zero usable candidates. SP-only preserved.
local function HumanMajors()
  local out = {};
  local seen = {};
  local function consider(id)
    if type(id) ~= "number" then return; end
    if seen[id] then return; end
    if Players == nil then return; end
    local okP, p = Try(function() return Players[id]; end);
    if not okP or p == nil then return; end
    local okH, human = Try(function() return p:IsHuman(); end);
    if not okH or not human then return; end
    local okM, major = Try(function() return p:IsMajor(); end);
    if okM and major then
      seen[id] = true;
      table.insert(out, { id = id, player = p });
    end
  end
  local function considerPlayer(pobj)
    if pobj == nil then return; end
    local okI, id = Try(function() return pobj:GetID(); end);
    if okI then consider(id); end
  end
  if PlayerManager ~= nil then
    local n0 = #out;
    local okIds, ids = Try(function()
      return PlayerManager.GetAliveMajorIDs();
    end);
    if okIds and ids ~= nil then
      Try(function()
        for _, id in ipairs(ids) do consider(id); end
      end);
    end
    if #out > n0 then return out; end
    x10log("GetAliveMajorIDs yielded nothing; trying Player objects");
    local okObjs, objs = Try(function()
      return PlayerManager.GetAliveMajors();
    end);
    if okObjs and objs ~= nil then
      Try(function()
        for _, pobj in ipairs(objs) do considerPlayer(pobj); end
      end);
    end
    if #out > n0 then return out; end
    x10log("no usable PlayerManager candidates; bounded index scan");
  else
    x10log("PlayerManager unavailable; bounded index scan");
  end
  for id = 0, 63 do consider(id); end
  return out;
end

local function PlayerCulture(entry)
  if entry == nil or entry.player == nil then return nil; end
  local ok, culture = Try(function() return entry.player:GetCulture(); end);
  if not ok or culture == nil then return nil; end
  return culture;
end

local function ConfigNumber(candidates)
  if GameConfiguration == nil then return nil; end
  for _, key in ipairs(candidates) do
    local ok, v = Try(function() return GameConfiguration.GetValue(key); end);
    if ok and type(v) == "number" then return v; end
  end
  return nil;
end

-- Resolve (copiesPerSource, enabledMask) or nil when disarmed or
-- unresolvable (fail closed + loud; never guess k). Native parity:
-- integral armed k -> k-1 extra slots per source (REPEAT copies);
-- fractional k activates zero copies (vanilla single slot);
-- k == 0 (incl. blank-as-0) and preset Off and invalid disarm.
local function ResolveCopiesAndMask()
  local k = nil;
  local preset = ConfigNumber({ "X10_MULTIPLIER_PRESET", "X10Preset" });
  if preset ~= nil then
    if preset == 0 then return nil; end
    if preset == 101 then
      local custom = ConfigNumber({ "X10_MULTIPLIER", "X10Custom" });
      if type(custom) ~= "number" or custom <= 0 or custom > 100 then
        return nil;
      end
      k = custom;
    elseif preset == 2 or preset == 3 or preset == 5 or preset == 10
        or preset == 20 or preset == 50 or preset == 100 then
      k = preset;
    else
      return nil;
    end
  else
    local custom = ConfigNumber({ "X10_MULTIPLIER", "X10Custom" });
    if type(custom) ~= "number" or custom <= 0 or custom > 100 then
      return nil;
    end
    k = custom;
  end
  local copies = 0;
  if k == math.floor(k) then copies = k - 1; end
  local mask = 0;
  for name, bit in pairs(MODULE_BITS) do
    local v = ConfigNumber({ MODULE_CONFIG_IDS[name],
                             MODULE_PARAM_IDS[name] });
    -- Absent key defaults ON (native declared defaults); exact
    -- 0/false reads OFF; anything else unreadable reads OFF.
    if v == nil or v == 1 or v == true then
      mask = mask + bit;
    end
  end
  return copies, mask;
end

-- Probe that policy enumeration + unlock queries work. Returns
-- (true, nil) or (false, reason). No CanSlotPolicy / slot-type /
-- obsolete machinery remains (removed 8B.4.4: unavailable here).
local function ProbePolicyAccess(culture)
  if GameInfo == nil then return false, "no GameInfo"; end
  local ok, iter = Try(function() return GameInfo.Policies(); end);
  if not ok or iter == nil then return false, "no Policies table"; end
  local first = nil;
  for row in iter do first = row; break; end
  if first == nil or first.Index == nil then
    return false, "policy rows lack Index";
  end
  local okU, resU = Try(function()
    return culture:IsPolicyUnlocked(first.Index);
  end);
  if not okU or type(resU) ~= "boolean" then
    return false, "IsPolicyUnlocked unavailable";
  end
  local okL, hasUnlock = Try(function()
    return culture.UnlockPolicy ~= nil;
  end);
  if not okL or not hasUnlock then
    return false, "UnlockPolicy unavailable";
  end
  return true, nil;
end

local function WonderOwned(player, buildingType)
  -- true / false / nil(unknown). Unknown fails closed + loud.
  if player == nil or GameInfo == nil then return nil; end
  local okB, brow = Try(function()
    return GameInfo.Buildings[buildingType];
  end);
  if not okB or brow == nil or brow.Index == nil then return nil; end
  local okC, cities = Try(function() return player:GetCities(); end);
  if not okC or cities == nil then return nil; end
  local found, failed = false, false;
  local okM = Try(function()
    for _, city in cities:Members() do
      local okG, bldgs = Try(function() return city:GetBuildings(); end);
      if okG and bldgs ~= nil then
        local okH, has = Try(function()
          return bldgs:HasBuilding(brow.Index);
        end);
        if okH and has then found = true; break; end
        if not okH then failed = true; end
      else
        failed = true;
      end
    end
    return true;
  end);
  if not okM then return nil; end
  if found then return true; end
  if failed then return nil; end
  return false;
end

local function PlayerHasTrait(playerID, traitType)
  -- true / false / nil(unknown -> caller treats as INACTIVE + loud;
  -- trait sources are permanent, so unknown is fail-closed here).
  if PlayerConfigurations == nil or GameInfo == nil then return nil; end
  local okC, cfg = Try(function()
    return PlayerConfigurations[playerID];
  end);
  if not okC or cfg == nil then return nil; end
  local okL, leader = Try(function()
    return cfg:GetLeaderTypeName();
  end);
  local okV, civ = Try(function()
    return cfg:GetCivilizationTypeName();
  end);
  if not okL and not okV then return nil; end
  local resolved = false;
  if okL and leader ~= nil then
    resolved = true;
    local okT, titer = Try(function()
      return GameInfo.LeaderTraits();
    end);
    if okT and titer ~= nil then
      for row in titer do
        if row.LeaderType == leader and row.TraitType == traitType then
          return true;
        end
      end
    else
      resolved = false;
    end
  end
  if okV and civ ~= nil then
    resolved = true;
    local okT, titer = Try(function()
      return GameInfo.CivilizationTraits();
    end);
    if okT and titer ~= nil then
      for row in titer do
        if row.CivilizationType == civ and row.TraitType == traitType then
          return true;
        end
      end
    else
      resolved = false;
    end
  end
  if resolved then return false; end
  return nil;
end

-- Active-source targets for one player: { slotType = count }.
-- A source contributes (copies) iff its module is enabled AND it is
-- active (wonder owned / trait held). Unknown wonder state fails
-- closed; unknown trait state fails closed (loud either way).
local knownActive = {};

local function PlayerTargets(entry, copies, mask)
  local targets = {};
  for _, src in ipairs(SOURCES) do
    local bit = MODULE_BITS[src.module] or 0;
    local enabled = true;
    local bb = bit;
    local mm = mask;
    while bb > 0 do
      if bb % 2 == 1 and mm % 2 == 0 then enabled = false; break; end
      bb = math.floor(bb / 2);
      mm = math.floor(mm / 2);
    end
    if enabled and copies > 0 then
      local active = nil;
      if src.kind == "building" then
        active = WonderOwned(entry.player, src.id);
      else
        active = PlayerHasTrait(entry.id, src.id);
      end
      if active == true then
        local key = entry.id .. "|" .. src.base;
        if knownActive[key] == nil then
          knownActive[key] = true;
          x10log("source active: " .. src.id
            .. " (+" .. tostring(copies) .. " " .. src.slot .. ")");
        end
        targets[src.slot] = (targets[src.slot] or 0) + copies;
      elseif active == nil then
        x10log("WARNING: source state unknown: " .. src.id
          .. " for player " .. tostring(entry.id)
          .. " (contributes 0)");
      end
    end
  end
  return targets;
end

local function AlreadyUnlockedByType(culture)
  local counts = {};
  local seen = 0;
  for row in GameInfo.Policies() do
    seen = seen + 1;
    if IsOurs(row.PolicyType) and row.Index ~= nil then
      local okU, unlocked = Try(function()
        return culture:IsPolicyUnlocked(row.Index);
      end);
      if okU and unlocked and row.GovernmentSlotType ~= nil then
        local t = row.GovernmentSlotType;
        counts[t] = (counts[t] or 0) + 1;
      end
    end
  end
  if seen == 0 then return nil; end
  return counts;
end

local function UnlockToTarget(culture, targets, have)
  local total = 0;
  local order = { "SLOT_MILITARY", "SLOT_DIPLOMATIC", "SLOT_ECONOMIC",
                  "SLOT_WILDCARD" };
  for _, slotType in ipairs(order) do
    local n = (targets[slotType] or 0) - (have[slotType] or 0);
    if n > 0 then
      for row in GameInfo.Policies() do
        if n <= 0 then break; end
        if IsOurs(row.PolicyType)
            and row.GovernmentSlotType == slotType
            and row.Index ~= nil then
          local okU, unlocked = Try(function()
            return culture:IsPolicyUnlocked(row.Index);
          end);
          if okU and not unlocked then
            local okL = Try(function()
              culture:UnlockPolicy(row.Index);
            end);
            if okL then
              n = n - 1;
              total = total + 1;
              x10log("unlocked " .. tostring(row.PolicyType));
            else
              x10log("UnlockPolicy failed for "
                .. tostring(row.PolicyType));
            end
          end
        end
      end
      if n > 0 then
        x10log("WARNING: target shortfall of " .. tostring(n)
          .. " for " .. slotType .. " (ran out of locked fillers)");
      end
    end
  end
  for slotType, want in pairs(targets) do
    local known = false;
    for _, k in ipairs(order) do
      if k == slotType then known = true; break; end
    end
    if not known and want > 0 then
      x10log("WARNING: target for unknown slot type "
        .. tostring(slotType) .. " x" .. tostring(want));
    end
  end
  return total;
end

local loggedDisarmed = false;

local function ReconcilePlayer(entry, reason)
  local copies, mask = ResolveCopiesAndMask();
  if copies == nil then
    if not loggedDisarmed then
      loggedDisarmed = true;
      x10log("X10 disarmed or configuration unreadable; no-op");
    end
    return;
  end
  local culture = PlayerCulture(entry);
  if culture == nil then
    x10log("no culture for player " .. tostring(entry.id)
      .. " [" .. tostring(reason) .. "]");
    return;
  end
  local okP, perr = ProbePolicyAccess(culture);
  if not okP then
    x10log("policy-access probe failed (" .. tostring(perr)
      .. "); unlocking nothing [" .. tostring(reason) .. "]");
    return;
  end
  local targets = PlayerTargets(entry, copies, mask);
  local have = AlreadyUnlockedByType(culture);
  if have == nil then
    x10log("filler census failed; unlocking nothing ["
      .. tostring(reason) .. "]");
    return;
  end
  local want, got = 0, 0;
  for _, c in pairs(targets) do want = want + c; end
  for _, c in pairs(have) do got = got + c; end
  if want > 0 or got > 0 then
    local parts = {};
    for _, slotType in ipairs({ "SLOT_MILITARY", "SLOT_DIPLOMATIC",
                                "SLOT_ECONOMIC", "SLOT_WILDCARD" }) do
      table.insert(parts, slotType .. " target="
        .. tostring(targets[slotType] or 0) .. " have="
        .. tostring(have[slotType] or 0));
    end
    x10log("player " .. tostring(entry.id) .. " "
      .. table.concat(parts, " ") .. " [" .. tostring(reason) .. "]");
  end
  local unlocked = UnlockToTarget(culture, targets, have);
  if unlocked > 0 then
    x10log("player " .. tostring(entry.id) .. " unlocked="
      .. tostring(unlocked) .. " [" .. tostring(reason) .. "]");
  end
end

local function ReconcileAll(reason)
  for _, entry in ipairs(HumanMajors()) do
    local okR, err = pcall(ReconcilePlayer, entry, reason);
    if not okR then
      x10log("reconcile failed for player " .. tostring(entry.id)
        .. ": " .. tostring(err));
    end
  end
end

local function HookEvents()
  local hooks = {
    { t = Events, name = "WonderCompleted" },
    { t = Events, name = "TurnBegin" },
    { t = Events, name = "LoadScreenClose" },
  };
  for _, h in ipairs(hooks) do
    if h.t ~= nil and h.t[h.name] ~= nil then
      local ok, err = pcall(function()
        h.t[h.name].Add(function() ReconcileAll(h.name); end);
      end);
      x10log("hook " .. h.name .. (ok and " ok" or " FAILED"));
    end
  end
end

x10log("loaded (dormant fillers; source-driven targets only)");
HookEvents();
ReconcileAll("init");
