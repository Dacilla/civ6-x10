// SCRATCH TEST REGISTRY — Toqui/pressure observability probe (Phase 6A).
// NOT production. This file answers ONE question: do identity-pressure
// definitions read back through the current store-lookup mechanism, or is
// the 2026-10-08 Toqui stored-form hold still in force?
//
// The eight rows below are the NEEDS_LIVE_PROBE backlog rows (6) plus the
// two held-out Toqui rows. All are unconditional ADDITIVE (kind 0,
// countLike 0); owners follow the row's home module (32=governors,
// 64=suzerain) with ALL modules enabled in the test game.
// NEVER copy these rows into build/X10ProductionRegistry.inc.
#pragma once
struct X10RegistryEntry {
    const char* modifierId;
    const char* argument;
    const char* official;
    int kind; // 0=ADDITIVE 1=COMBAT 2=PROBABILITY 3=DISCOUNT
    int countLike; // runtime integral-result check required
    int owners; // module bitmask
};
static const X10RegistryEntry kX10ProductionRegistry[] = {
    {"TOQUI_DOMESTIC_LOYALTY", "Amount", "4", 0, 0, 32},
    {"TOQUI_FOREIGN_LOYALTY", "Amount", "4", 0, 0, 32},
    {"CARDINAL_BISHOP_PRESSURE", "Amount", "100", 0, 0, 32},
    {"GOVERNOR_PROMOTION_OWLS_OF_MINERVA_3_LOYALTY_FROM_COUNTERSPY", "Amount", "4", 0, 0, 32},
    {"MINOR_CIV_PRESLAV_ARMORY_IDENTITY_BONUS", "Amount", "2", 0, 0, 64},
    {"MINOR_CIV_PRESLAV_BARRACKS_STABLE_IDENTITY_BONUS", "Amount", "2", 0, 0, 64},
    {"MINOR_CIV_PRESLAV_MILITARY_ACADEMY_IDENTITY_BONUS", "Amount", "2", 0, 0, 64},
    {"MINOR_CIV_VATICAN_CITY_GREAT_PERSON_RELIGIOUS_PRESSURE", "Amount", "400", 0, 0, 64},
};
static const int kX10ProductionRegistryCount = 8;
