-- X10SlotManager.lua
-- On-demand Reserve Policy unlocker (Phase 8B.4).
--
-- Runs as a gameplay script (AddGameplayScripts, simulation context).
-- The 700 Reserve policies ship DORMANT (ExplicitUnlock, no civic), so
-- nothing is visible until this manager unlocks the deficit for the
-- player's CURRENT policy slots. At ordinary Code of Laws the deficit
-- is zero and the picker stays clean.
--
-- Safety properties (all load-bearing, all human-gated in P0C):
--   * every engine call is pcall-guarded; any failure aborts that run
--     loudly (log line) and unlocks nothing new;
--   * deficit math is satisfiability-exact: typed slots take same-type
--     cards only, wildcard slots absorb any remainder, great-person
--     cards are conservatively ignored (extra fillers, never too few);
--   * idempotent: already-unlocked fillers are skipped via
--     IsPolicyUnlocked; re-running changes nothing;
--   * human majors only (AI never needs confirm-gate help);
--   * no-ops when X10 resolves disarmed; manages (with a loud log line)
--     when configuration is unreadable rather than stranding slots.
-- No auto-slotting ships here: slotting stays manual until a runtime-
-- proven pass enables it (see docs/PHASE_8B.md section 9).

local FILLER_MATCH = "POLICY_X10_FILLER_";
local SLOT_TYPES = { "SLOT_MILITARY", "SLOT_DIPLOMATIC", "SLOT_ECONOMIC", "SLOT_WILDCARD" };

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

local function HumanMajors()
  local out = {};
  if Players == nil then return out; end
  local ok, count = Try(function() return #Players; end);
  if not ok or type(count) ~= "number" then return out; end
  for i = 0, count - 1 do
    local okP, p = Try(function() return Players[i]; end);
    if okP and p ~= nil then
      local okH, human = Try(function() return p:IsHuman(); end);
      local okM, major = Try(function() return p:IsMajor(); end);
      if okH and human and okM and major then
        table.insert(out, { id = i, player = p });
      end
    end
  end
  return out;
end

local function PlayerCulture(entry)
  if entry == nil or entry.player == nil then return nil; end
  local ok, culture = Try(function() return entry.player:GetCulture(); end);
  if not ok or culture == nil then return nil; end
  return culture;
end

-- Configuration gate. Returns true (manage), false (X10 disarmed:
-- no-op), or nil plus a loud log when unreadable (manage anyway so
-- slots are never stranded by an API-shape mismatch).
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
      if type(custom) ~= "number" or custom < 0 or custom > 100 then
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
  -- No preset key: legacy custom path (or unreadable config).
  local custom = ConfigNumber({ "X10_MULTIPLIER", "X10Custom" });
  if custom ~= nil then
    if type(custom) ~= "number" or custom < 0 or custom > 100 then
      return false;
    end
    return true;
  end
  x10log("configuration unreadable; managing anyway (never strand slots)");
  return true;
end

local function NormalizeSlotType(st)
  if type(st) == "string" then return st; end
  if type(st) == "number" and GameInfo ~= nil then
    local ok, iter = Try(function() return GameInfo.GovernmentSlots(); end);
    if ok and iter ~= nil then
      for row in iter do
        if row.Index == st then return row.GovernmentSlotType; end
      end
    end
  end
  return nil;
end

local function CurrentSlots(culture)
  local ok, n = Try(function() return culture:GetNumPolicySlots(); end);
  if not ok or type(n) ~= "number" or n <= 0 then return nil; end
  local out = {};
  for i = 0, n - 1 do
    local okS, st = Try(function() return culture:GetSlotType(i); end);
    if okS and st ~= nil then
      local t = NormalizeSlotType(st);
      if t ~= nil then table.insert(out, t); end
    end
  end
  if #out == 0 then return nil; end
  return out;
end

-- Probe that policy enumeration + unlock queries work. Returns
-- (true, firstRow) or (false, reason). A failed probe aborts the run:
-- under-counting real cards would over-unlock (flood), and missing
-- unlock APIs would strand slots silently.
local function ProbePolicyAccess(culture)
  if GameInfo == nil then return false, "no GameInfo"; end
  local ok, iter = Try(function() return GameInfo.Policies(); end);
  if not ok or iter == nil then return false, "no Policies table"; end
  local first = nil;
  for row in iter do first = row; break; end
  if first == nil or first.Index == nil then
    return false, "policy rows lack Index";
  end
  local okU, res = Try(function()
    return culture:IsPolicyUnlocked(first.Index);
  end);
  if not okU or type(res) ~= "boolean" then
    return false, "IsPolicyUnlocked unavailable";
  end
  local okL = Try(function()
    return culture.UnlockPolicy ~= nil;
  end);
  if not okL then return false, "UnlockPolicy unavailable"; end
  return true, nil;
end

local function RealUnlockedByType(culture)
  local counts = { SLOT_MILITARY = 0, SLOT_DIPLOMATIC = 0,
                   SLOT_ECONOMIC = 0, SLOT_WILDCARD = 0 };
  local seen = 0;
  for row in GameInfo.Policies() do
    seen = seen + 1;
    if not IsOurs(row.PolicyType) and row.Index ~= nil
        and counts[row.GovernmentSlotType] ~= nil then
      local okU, unlocked = Try(function()
        return culture:IsPolicyUnlocked(row.Index);
      end);
      if okU and unlocked then
        counts[row.GovernmentSlotType] = counts[row.GovernmentSlotType] + 1;
      end
    end
  end
  if seen == 0 then return nil; end
  return counts;
end

-- Exact satisfiability deficit. Typed slots consume same-type real
-- cards first; wildcard slots absorb any remainder; great-person cards
-- are ignored (conservative: extra fillers, never too few).
local function Deficit(slots, real)
  local need = { SLOT_MILITARY = 0, SLOT_DIPLOMATIC = 0,
                 SLOT_ECONOMIC = 0, SLOT_WILDCARD = 0 };
  local have = { SLOT_MILITARY = real.SLOT_MILITARY or 0,
                 SLOT_DIPLOMATIC = real.SLOT_DIPLOMATIC or 0,
                 SLOT_ECONOMIC = real.SLOT_ECONOMIC or 0,
                 SLOT_WILDCARD = real.SLOT_WILDCARD or 0 };
  local wild = 0;
  for _, t in ipairs(slots) do
    if t == "SLOT_WILDCARD" then
      wild = wild + 1;
    elseif have[t] ~= nil and have[t] > 0 then
      have[t] = have[t] - 1;
    elseif need[t] ~= nil then
      need[t] = need[t] + 1;
    end
  end
  local surplus = (have.SLOT_MILITARY or 0) + (have.SLOT_DIPLOMATIC or 0)
    + (have.SLOT_ECONOMIC or 0) + (have.SLOT_WILDCARD or 0);
  if wild > surplus then need.SLOT_WILDCARD = wild - surplus; end
  return need;
end

local function UnlockDeficit(culture, need)
  local total = 0;
  for _, slotType in ipairs(SLOT_TYPES) do
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
            local okL, err = Try(function()
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
        x10log("WARNING: unfilled deficit of " .. tostring(n)
          .. " for " .. slotType .. " (ran out of locked fillers)");
      end
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
  local real = RealUnlockedByType(culture);
  if real == nil then
    x10log("real-card census failed; unlocking nothing ["
      .. tostring(reason) .. "]");
    return;
  end
  local need = Deficit(slots, real);
  local n = (need.SLOT_MILITARY or 0) + (need.SLOT_DIPLOMATIC or 0)
    + (need.SLOT_ECONOMIC or 0) + (need.SLOT_WILDCARD or 0);
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

x10log("loaded (dormant fillers; on-demand unlock only)");
HookEvents();
ReconcileAll("init");
