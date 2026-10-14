-- X10SlotManager.lua
-- On-demand Reserve Policy unlocker (Phase 8B.4, hardened 8B.4.1).
--
-- Runs as a gameplay script (AddGameplayScripts, simulation context --
-- the Wonder-x10 precedent). The 700 Reserve policies ship DORMANT
-- (ExplicitUnlock, no civic), so nothing is visible until this manager
-- unlocks the deficit for the players' CURRENT policy slots. At
-- ordinary Code of Laws the deficit is zero and the picker stays clean.
--
-- Deficit algorithm (satisfiability over ACTUAL engine legality, not
-- type counting): enumerate current slot indices, enumerate unlocked
-- non-X10 policies minus obsolete ones, build policy->slot eligibility
-- with CanSlotPolicy(index, slotIndex), maximum bipartite match
-- (augmenting path), and unlock one Reserve filler of the
-- corresponding slot type per unmatched slot.
--
-- Safety properties (all load-bearing, all human-gated in P0C):
--   * every engine call is pcall-guarded; a missing/unusable API
--     (enumeration, IsPolicyUnlocked/Obsolete, CanSlotPolicy,
--     UnlockPolicy) aborts that run loudly and unlocks nothing new
--     (fail closed, never a claimed-exact deficit);
--   * idempotent: already-unlocked fillers are skipped via
--     IsPolicyUnlocked; re-running changes nothing;
--   * human majors only (AI never needs confirm-gate help), discovered
--     via PlayerManager.GetAliveMajors with a bounded index-scan
--     fallback (never Lua length over Players);
--   * no-ops when X10 resolves disarmed (Custom 0 included, mirroring
--     native k==0 normalization); manages (with a loud log line) only
--     when configuration is unreadable rather than stranding slots.
-- No auto-slotting ships here: slotting stays manual until a runtime-
-- proven pass enables it (see docs/PHASE_8B.md section 9).

local FILLER_MATCH = "POLICY_X10_FILLER_";

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
-- GetID (the bundled reference types it as Player[]); last: bounded
-- 0..63 index scan. Each stage runs only if the previous yielded zero
-- usable candidates (not merely on throw): GetAliveMajors-style calls
-- succeed while returning unusable shapes, which must NOT read as
-- "no humans". SP-only behavior preserved (normally one entry).
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

-- Configuration gate. Returns true (manage) or false (X10 disarmed:
-- no-op). Native parity: Custom 0 (and blank-as-0) normalizes to
-- DISARMED like preset Off. Unreadable config manages with a loud log
-- rather than stranding slots.
local function ConfigNumber(candidates)
  if GameConfiguration == nil then return nil; end
  for _, key in ipairs(candidates) do
    local ok, v = Try(function() return GameConfiguration.GetValue(key); end);
    if ok and type(v) == "number" then return v; end
  end
  return nil;
end

local function ShouldManage()
  local preset = ConfigNumber({ "X10_MULTIPLIER_PRESET", "X10Preset" });
  if preset ~= nil then
    if preset == 0 then return false; end
    if preset == 101 then
      local custom = ConfigNumber({ "X10_MULTIPLIER", "X10Custom" });
      if type(custom) ~= "number" or custom <= 0 or custom > 100 then
        return false;
      end
      return true;
    end
    if preset == 2 or preset == 3 or preset == 5 or preset == 10
        or preset == 20 or preset == 50 or preset == 100 then
      return true;
    end
    return false;
  end
  local custom = ConfigNumber({ "X10_MULTIPLIER", "X10Custom" });
  if custom ~= nil then
    if type(custom) ~= "number" or custom <= 0 or custom > 100 then
      return false;
    end
    return true;
  end
  x10log("configuration unreadable; managing anyway (never strand slots)");
  return true;
end

-- Probe that policy enumeration + all three legality/unlock queries
-- work. Returns (true, nil) or (false, reason). A failed probe aborts
-- the run: an exact deficit cannot be claimed without these.
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
  local okO, resO = Try(function()
    return culture:IsPolicyObsolete(first.Index);
  end);
  if not okO or type(resO) ~= "boolean" then
    return false, "IsPolicyObsolete unavailable";
  end
  local okC, hasCan = Try(function()
    return culture.CanSlotPolicy ~= nil;
  end);
  if not okC or not hasCan then
    return false, "CanSlotPolicy unavailable";
  end
  local okL, hasUnlock = Try(function()
    return culture.UnlockPolicy ~= nil;
  end);
  if not okL or not hasUnlock then
    return false, "UnlockPolicy unavailable";
  end
  return true, nil;
end

local function CurrentSlots(culture)
  local ok, n = Try(function() return culture:GetNumPolicySlots(); end);
  if not ok or type(n) ~= "number" or n <= 0 then return nil; end
  local out = {};
  for i = 0, n - 1 do
    local okS, st = Try(function() return culture:GetSlotType(i); end);
    if okS and st ~= nil then
      local t = st;
      if type(st) == "number" and GameInfo ~= nil then
        t = nil;
        local okG, giter = Try(function()
          return GameInfo.GovernmentSlots();
        end);
        if okG and giter ~= nil then
          for row in giter do
            if row.Index == st then
              t = row.GovernmentSlotType;
              break;
            end
          end
        end
      end
      if type(t) == "string" then
        table.insert(out, { slot = i, slotType = t });
      end
    end
  end
  if #out == 0 then return nil; end
  return out;
end

-- Unlocked, non-obsolete, non-X10 policies: array of { index, slotType }.
-- Great-person cards are kept (CanSlotPolicy decides legality, not us).
local function EligibleRealPolicies(culture)
  local out = {};
  local seen = 0;
  for row in GameInfo.Policies() do
    seen = seen + 1;
    if not IsOurs(row.PolicyType) and row.Index ~= nil then
      local okU, unlocked = Try(function()
        return culture:IsPolicyUnlocked(row.Index);
      end);
      if okU and unlocked then
        local okO, obsolete = Try(function()
          return culture:IsPolicyObsolete(row.Index);
        end);
        if okO and not obsolete then
          table.insert(out, { index = row.Index,
                              slotType = row.GovernmentSlotType });
        end
      end
    end
  end
  if seen == 0 then return nil; end
  return out;
end

-- Edge test through the engine: can this policy fill this slot?
local function EngineCanSlot(culture, policyIndex, slotIndex)
  local ok, res = Try(function()
    return culture:CanSlotPolicy(policyIndex, slotIndex);
  end);
  return ok and res == true;
end

-- Maximum bipartite matching (policies -> slots) by augmenting path
-- (Kuhn). Returns matchSlot[slotPos] = policyPos or nil.
local function MaximumMatching(culture, policies, slots)
  local adj = {};
  for pi, pol in ipairs(policies) do
    adj[pi] = {};
    for si, slot in ipairs(slots) do
      if EngineCanSlot(culture, pol.index, slot.slot) then
        table.insert(adj[pi], si);
      end
    end
  end
  local matchSlot = {};
  local function Dfs(pi, seen)
    for _, si in ipairs(adj[pi]) do
      if not seen[si] then
        seen[si] = true;
        if matchSlot[si] == nil or Dfs(matchSlot[si], seen) then
          matchSlot[si] = pi;
          return true;
        end
      end
    end
    return false;
  end
  for pi = 1, #policies do
    Dfs(pi, {});
  end
  return matchSlot;
end

-- One Reserve filler of the corresponding slot type per unmatched slot.
local function DeficitFromUnmatched(slots, matchSlot)
  local need = {};
  for si, slot in ipairs(slots) do
    if matchSlot[si] == nil then
      need[slot.slotType] = (need[slot.slotType] or 0) + 1;
    end
  end
  return need;
end

local function UnlockDeficit(culture, need)
  local total = 0;
  local order = { "SLOT_MILITARY", "SLOT_DIPLOMATIC", "SLOT_ECONOMIC",
                  "SLOT_WILDCARD", "SLOT_GREAT_PERSON" };
  for _, slotType in ipairs(order) do
    local n = need[slotType] or 0;
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
      -- Wildcard slots accept any card: typed surplus could cover them,
      -- but per-slot-type fillers are always legal there, so any
      -- remainder is still satisfiable by construction.
      if n > 0 then
        x10log("WARNING: unfilled deficit of " .. tostring(n)
          .. " for " .. slotType .. " (ran out of locked fillers)");
      end
    end
  end
  -- Any other slot type (future): loudly report, unlock nothing blind.
  for slotType, n in pairs(need) do
    local known = false;
    for _, k in ipairs(order) do
      if k == slotType then known = true; break; end
    end
    if not known and n > 0 then
      x10log("WARNING: unmatched unknown slot type " .. tostring(slotType)
        .. " x" .. tostring(n) .. " (no filler family; manual fill needed)");
    end
  end
  return total;
end

local function ReconcilePlayer(entry, reason)
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
  local slots = CurrentSlots(culture);
  if slots == nil then
    x10log("slot enumeration unavailable; unlocking nothing ["
      .. tostring(reason) .. "]");
    return;
  end
  local policies = EligibleRealPolicies(culture);
  if policies == nil then
    x10log("policy census failed; unlocking nothing ["
      .. tostring(reason) .. "]");
    return;
  end
  local matchSlot = MaximumMatching(culture, policies, slots);
  local need = DeficitFromUnmatched(slots, matchSlot);
  local n = 0;
  for _, c in pairs(need) do n = n + c; end
  if n <= 0 then return; end
  local unlocked = UnlockDeficit(culture, need);
  x10log("player " .. tostring(entry.id) .. " deficit unlocked="
    .. tostring(unlocked) .. " [" .. tostring(reason) .. "]");
end

local function ReconcileAll(reason)
  local ok, manage = Try(ShouldManage);
  if ok and manage == false then return; end
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
    { t = Events, name = "GovernmentPolicyChanged" },
    { t = Events, name = "GovernmentChanged" },
    { t = Events, name = "CivicCompleted" },
    { t = Events, name = "TurnBegin" },
    { t = Events, name = "LoadScreenClose" },
  };
  if GameEvents ~= nil then
    table.insert(hooks, { t = GameEvents, name = "PlayerTurnStarted" });
    table.insert(hooks, { t = GameEvents, name = "PlayerDoTurn" });
  end
  for _, h in ipairs(hooks) do
    if h.t ~= nil and h.t[h.name] ~= nil then
      local ok, err = pcall(function()
        h.t[h.name].Add(function() ReconcileAll(h.name); end);
      end);
      x10log("hook " .. h.name .. (ok and " ok" or " FAILED"));
    end
  end
end

x10log("loaded (dormant fillers; legality-matched on-demand unlock only)");
HookEvents();
ReconcileAll("init");
