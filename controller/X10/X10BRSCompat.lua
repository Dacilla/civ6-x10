-- X10BRSCompat.lua
-- BRS / Extended Policy Cards calculated-preview compatibility
-- (Phase 8B.4, wired 8B.4.1). Executes in its own minimal UI context
-- (X10BRSCompat, via AddUserInterfaces + same-basename auto-execution --
-- the Better Report Screen RealModifierAnalysis pattern) AFTER
-- explicitly including X10BRSData.lua.
--
-- Problem: RMA (Better Report Screen's RealModifierAnalysis) memoizes
-- ModifierArguments read from gameplay SQLite (DB.Query), which CE never
-- rewrites -- native X10 transforms live only in GameCore memory. So BRS
-- policy pages and EPC card effects show vanilla values while gameplay
-- is scaled (e.g. God King +1/+1 preview vs +10/+10 live).
--
-- Mechanism (additive, no BRS/EPC files touched):
-- FetchAndCacheData returns the memoized table BY REFERENCE
-- (tModifiers[id]), and DecodeModifier/CalculateModifierEffect read
-- Arguments from that same table. Before delegating to the ORIGINAL
-- CalculateModifierEffect, this layer recomputes X10-effective arguments
-- from the generated registry (same officials, kinds, count-like gates,
-- owner bits, and k as the native engine) and overwrites the cached
-- Arguments IN PLACE. Audited callers (BRSPage_Policy Policy/Belief,
-- BRSPage_Minor Trait, EPC GovernmentScreen Policy) index
-- ExposedMembers.RMA at call time, so every covered preview path flows
-- through the patched cache with zero file replacement. Generated data
-- covers the full non-REPEAT registry, but only Policy/Belief/Trait
-- objects have a wrapper path that consumes them (see LINK).
--
-- Safety properties (all load-bearing, all human-gated in P1):
--   * no-ops when BRS is absent (ExposedMembers.RMA nil) or when X10
--     resolves disarmed/invalid (cache left vanilla);
--   * patch values derive from OUR officials, never read-modify-write,
--     so re-patching is idempotent and can never double-scale;
--   * count-like inexact results are left vanilla (native refuses too);
--   * the wrapper never throws: any error falls back to the original
--     function on the unpatched cache (today's behavior);
--   * re-wraps safely if RMA re-initializes (wrapper identity tracked
--     in the shared table).
-- REPEAT slot rows are excluded from the data (not numerical effects).
-- Requires live P1 witnesses; see docs/PHASE_8B.md section 9.
--
-- Runtime proof (P1 is invalid without these Lua.log lines):
--   [X10BRSCompat] context loaded
--   [X10BRSCompat] generated data loaded: 1788 entries
--   [X10BRSCompat] RMA found|deferred ...
--   [X10BRSCompat] installed ...

print("[X10BRSCompat] context loaded");

local okInc, errInc = pcall(include, "X10BRSData");
if not okInc or X10BRSData == nil or X10BRSData.entries == nil then
  print("[X10BRSCompat] generated data missing; idle");
  return;
end
print("[X10BRSCompat] generated data loaded: "
  .. tostring(#X10BRSData.entries) .. " entries");

local LINK = {
  Policy = { table = "PolicyModifiers", field = "PolicyType" },
  Belief = { table = "BeliefModifiers", field = "BeliefType" },
  Trait = { table = "TraitModifiers", field = "TraitType" },
};

local KIND_ADDITIVE = 0;
local KIND_COMBAT = 1;
local KIND_PROBABILITY = 2;
local KIND_DISCOUNT = 3;
local KIND_VECTOR = 4;
local KIND_DELTA = 5;

local MODULE_PARAM_IDS = {
  "X10ModuleTraits", "X10ModulePolicies", "X10ModuleGovernments",
  "X10ModulePantheons", "X10ModuleWonders", "X10ModuleGovernors",
  "X10ModuleSuzerain", "X10ModulePromotions", "X10ModuleDedications",
  "X10ModuleModes", "X10ModuleReligion", "X10ModuleGreatPeople",
  "X10ModuleProjects",
};
local MODULE_CONFIG_IDS = {
  "X10_MODULE_TRAITS", "X10_MODULE_POLICIES", "X10_MODULE_GOVERNMENTS",
  "X10_MODULE_PANTHEONS", "X10_MODULE_WONDERS", "X10_MODULE_GOVERNORS",
  "X10_MODULE_SUZERAIN", "X10_MODULE_PROMOTIONS", "X10_MODULE_DEDICATIONS",
  "X10_MODULE_MODES", "X10_MODULE_RELIGION", "X10_MODULE_GREATPEOPLE",
  "X10_MODULE_PROJECTS",
};

local PRESET_VALUES = { [0] = true, [2] = true, [3] = true, [5] = true,
  [10] = true, [20] = true, [50] = true, [100] = true };

local function x10log(msg)
  print("[X10BRSCompat] " .. tostring(msg));
end

local function Try(fn)
  local ok, r = pcall(fn);
  if ok then return true, r; end
  return false, nil;
end

local function ConfigNumber(candidates)
  if GameConfiguration == nil then return nil; end
  for _, key in ipairs(candidates) do
    local ok, v = Try(function() return GameConfiguration.GetValue(key); end);
    if ok and type(v) == "number" then return v; end
  end
  return nil;
end

-- Returns k, enabledMask, or nil when disarmed/unresolvable (identity).
-- Native parity: k == 0 normalizes to DISARMED (like preset Off);
-- blank custom reaches this state as INT32 0.
local function ResolveArmed()
  local k = nil;
  local preset = ConfigNumber({ "X10_MULTIPLIER_PRESET", "X10Preset" });
  if preset ~= nil then
    if preset == 0 then return nil; end
    if preset == 101 then
      local c = ConfigNumber({ "X10_MULTIPLIER", "X10Custom" });
      if type(c) ~= "number" or c <= 0 or c > 100 then return nil; end
      k = c;
    elseif PRESET_VALUES[preset] then
      k = preset;
    else
      return nil;
    end
  else
    local c = ConfigNumber({ "X10_MULTIPLIER", "X10Custom" });
    if type(c) ~= "number" or c <= 0 or c > 100 then return nil; end
    k = c;
  end
  -- Module mask: absent key defaults ON (native declared defaults);
  -- exact 0/false reads OFF; anything else unreadable reads OFF
  -- (fail-closed, mirroring native TryGetConfigBool).
  local mask = 0;
  local bit = 1;
  for i = 1, 13 do
    local v = ConfigNumber({ MODULE_CONFIG_IDS[i], MODULE_PARAM_IDS[i] });
    local on = false;
    if v == nil then
      on = true;
    elseif v == 1 or v == true then
      on = true;
    end
    if on then mask = mask + bit; end
    bit = bit * 2;
  end
  return k, mask;
end

local function RoundHalfAway(v)
  if v >= 0 then return math.floor(v + 0.5); end
  return math.ceil(v - 0.5);
end

-- FLOAT32 half-ULP of the stored k (mirrors the native kErr source
-- quantization; frexp form is exact for normal floats).
local function Float32HalfUlp(x)
  if x == 0 or x ~= x then return 0; end
  local _, e = math.frexp(math.abs(x));
  return 2 ^ (e - 25);
end

local function CountApplies(official, k, kErr, isDelta)
  local v = official * (isDelta and (k - 1.0) or k);
  local r = RoundHalfAway(v);
  local tol = math.abs(official) * kErr + 1e-9 * math.max(1.0, math.abs(v));
  return tol < 0.5 and math.abs(v - r) <= tol;
end

-- Mirrors X10Transforms::Apply formatting: %.6g generally, %.2f combat.
-- Returns the replacement string, or nil to leave vanilla (refusal).
local function ApplyEntry(e, k)
  local official = tonumber(e.official);
  if official == nil then return nil; end
  local kErr = Float32HalfUlp(k);
  if e.countLike == 1
      and not CountApplies(official, k, kErr, e.kind == KIND_DELTA) then
    return nil;
  end
  if e.kind == KIND_ADDITIVE then
    return string.format("%.6g", official * k);
  elseif e.kind == KIND_COMBAT then
    if official < 0 then
      return string.format("%.6g", official * k);
    end
    local inner = k * math.exp(official / 25.0) - (k - 1.0);
    if inner <= 0 then return nil; end
    return string.format("%.2f", 25.0 * math.log(inner));
  elseif e.kind == KIND_PROBABILITY then
    local unitPct = math.abs(official) > 1.0;
    local frac = official;
    if unitPct then frac = official / 100.0; end
    if frac < 0.0 or frac > 1.0 then return nil; end
    local out = 1.0 - (1.0 - frac) ^ k;
    if unitPct then out = out * 100.0; end
    return string.format("%.6g", out);
  elseif e.kind == KIND_DISCOUNT then
    local d = math.abs(official) / 100.0;
    if d < 0.0 or d > 1.0 then return nil; end
    local out = (1.0 - (1.0 - d) ^ k) * 100.0;
    if official < 0 then out = -out; end
    return string.format("%.6g", out);
  elseif e.kind == KIND_VECTOR then
    local parts = {};
    local commas = 0;
    for i = 1, string.len(e.official) do
      if string.sub(e.official, i, i) == "," then commas = commas + 1; end
    end
    for elem in string.gmatch(e.official, "([^,]+)") do
      local v = tonumber(elem);
      if v == nil or v ~= v or math.abs(v) == math.huge then
        return nil;
      end
      table.insert(parts, string.format("%.6g", v * k));
    end
    if #parts < 2 or #parts ~= commas + 1 then return nil; end
    return table.concat(parts, ",");
  elseif e.kind == KIND_DELTA then
    return string.format("%.6g", official * (k - 1.0));
  end
  return nil;
end

-- Subset test without bitwise operators (Lua-version safe).
local function OwnersCovered(mask, need)
  while need > 0 do
    if need % 2 == 1 and mask % 2 == 0 then return false; end
    need = math.floor(need / 2);
    mask = math.floor(mask / 2);
  end
  return true;
end

local byId = nil;
local function IndexData()
  if byId ~= nil then return byId; end
  if X10BRSData == nil or X10BRSData.entries == nil then return nil; end
  byId = {};
  for _, e in ipairs(X10BRSData.entries) do
    local l = byId[e.id];
    if l == nil then l = {}; byId[e.id] = l; end
    table.insert(l, e);
  end
  return byId;
end

local function PatchOne(mid, k, mask, RMA)
  local list = byId[mid];
  if list == nil then return; end
  local okF, t = Try(function() return RMA.FetchAndCacheData(mid); end);
  if not okF or t == nil or t.Arguments == nil then return; end
  for _, e in ipairs(list) do
    if OwnersCovered(mask, e.owners) then
      local scaled = ApplyEntry(e, k);
      if scaled ~= nil then
        t.Arguments[e.arg] = scaled;
      end
    end
  end
end

local function PatchForCall(sObject, sObjectType, RMA)
  local link = LINK[sObject];
  if link == nil or GameInfo == nil then return; end
  local k, mask = ResolveArmed();
  if k == nil then return; end
  if IndexData() == nil then return; end
  local okT, tbl = Try(function() return GameInfo[link.table](); end);
  if not okT or tbl == nil then return; end
  for row in tbl do
    if row[link.field] == sObjectType then
      local mid = row.ModifierId or row.ModifierID;
      if type(mid) == "string" then PatchOne(mid, k, mask, RMA); end
    end
  end
end

local function Install()
  if ExposedMembers == nil then return false; end
  local RMA = ExposedMembers.RMA;
  if RMA == nil or RMA.CalculateModifierEffect == nil
      or RMA.FetchAndCacheData == nil then
    return false;
  end
  if ExposedMembers.X10BRSWrapper ~= nil
      and RMA.CalculateModifierEffect == ExposedMembers.X10BRSWrapper then
    return true;
  end
  local orig = RMA.CalculateModifierEffect;
  local wrapper = function(a, b, c, d, e)
    pcall(PatchForCall, a, b, RMA);
    return orig(a, b, c, d, e);
  end
  RMA.CalculateModifierEffect = wrapper;
  ExposedMembers.X10BRSWrapper = wrapper;
  x10log("installed (cache-patch wrapper around CalculateModifierEffect)");
  return true;
end

if Install() then
  x10log("RMA found; wrapper active");
else
  -- RMA not present yet (absent, or loads later): retry on late UI
  -- events. Silent no-op forever when BRS is absent.
  local function Retry()
    if pcall(Install) then
      x10log("RMA found late; wrapper active");
    end
  end
  if Events ~= nil then
    if Events.LoadScreenClose ~= nil then
      pcall(function()
        Events.LoadScreenClose.Add(function() Retry(); end);
      end);
    end
    if Events.GovernmentPolicyChanged ~= nil then
      pcall(function()
        Events.GovernmentPolicyChanged.Add(function() Retry(); end);
      end);
    end
  end
  x10log("RMA deferred (idle when BRS absent)");
end
