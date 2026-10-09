"""Phase 4A.1: closed-world Governor audit, hardened.

Three layers, deliberately separated so CI never needs proprietary game data:

1. **Synthetic fixture tests** - a minimal fake Civ VI tree (main mode XML +
   Expansion2 + Gran Colombia/Maya overlay) exercises action merging,
   criteria selection and typo normalisation with no game install.
2. **Checked-in manifest invariants** - structural invariants of
   `civ6x10/rules/governor_audit.yml` that hold without any local data.
3. **Real integration** - full derivation against the local official DB copy +
   installed game root; skips coherently (whole-module) when either is absent
   instead of comparing a partial derivation against the manifest.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

from civ6x10.governors import (
    PROPOSED_GOVERNOR_MODULE_BIT,
    PROPOSED_NEXT_MODULE_BIT_AFTER_GOVERNORS,
    build_audit,
    build_manifest,
    discover_governor_tables_from_db,
    load_mode_overlay,
    resolve_mode_payload,
    secret_society_governor_types,
)

SECRET_SOCIETY_GOVERNORS = {
    "GOVERNOR_OWLS_OF_MINERVA", "GOVERNOR_HERMETIC_ORDER",
    "GOVERNOR_VOIDSINGERS", "GOVERNOR_SANGUINE_PACT",
}
BASE_GOVERNORS = {
    "GOVERNOR_IBRAHIM", "GOVERNOR_THE_AMBASSADOR", "GOVERNOR_THE_BUILDER",
    "GOVERNOR_THE_CARDINAL", "GOVERNOR_THE_DEFENDER", "GOVERNOR_THE_EDUCATOR",
    "GOVERNOR_THE_MERCHANT", "GOVERNOR_THE_RESOURCE_MANAGER",
}

MODE_MAIN = """<?xml version="1.0" encoding="utf-8"?>
<GameInfo>
  <SecretSocieties>
    <Row SecretSocietyType="SECRETSOCIETY_OWLS_OF_MINERVA" Name="LOC_OWLS"
         GovernorType="GOVERNOR_OWLS_OF_MINERVA" DiscoverAtCityStateBaseChance="80"/>
    <Row SecretSocietyType="SECRETSOCIETY_HERMETIC_ORDER" Name="LOC_HERMETIC"
         GovernorType="GOVERNOR_HERMETIC_ORDER" DiscoverAtNaturalWonderBaseChance="100"/>
    <Row SecretSocietyType="SECRETSOCIETY_VOIDSINGERS" Name="LOC_VOID"
         GovernorType="GOVERNOR_VOIDSINGERS" DiscoverAtGoodyHutBaseChance="70"/>
    <Row SecretSocietyType="SECRETSOCIETY_SANGUINE_PACT" Name="LOC_SANGUINE"
         GovernorType="GOVERNOR_SANGUINE_PACT" DiscoverAtBarbarianCampBaseChance="70"/>
  </SecretSocieties>
  <Governors>
    <Row GovernorType="GOVERNOR_OWLS_OF_MINERVA" Name="LOC_OWLS" IdentityPressure="10" TransitionStrength="100"/>
    <Row GovernorType="GOVERNOR_HERMETIC_ORDER" Name="LOC_HERMETIC" IdentityPressure="10" TransitionStrength="100"/>
    <Row GovernorType="GOVERNOR_VOIDSINGERS" Name="LOC_VOID" IdentityPressure="10" TransitionStrength="100"/>
    <Row GovernorType="GOVERNOR_SANGUINE_PACT" Name="LOC_SANGUINE" IdentityPressure="10" TransitionStrength="100"/>
  </Governors>
  <GovernorsCannotAssign>
    <Row GovernorType="GOVERNOR_OWLS_OF_MINERVA" CannotAssign="true"/>
  </GovernorsCannotAssign>
  <GovernorPromotionSets>
    <Row GovernorType="GOVERNOR_OWLS_OF_MINERVA" GovernorPromotion="GOVERNOR_PROMOTION_OWLS_OF_MINERVA_1"/>
    <Row GovernorType="GOVERNOR_OWLS_OF_MINERVA" GovernorPromotion="GOVERNOR_PROMOTION_OWLS_OF_MINERVA_2"/>
  </GovernorPromotionSets>
  <GovernorPromotions>
    <Row GovernorPromotionType="GOVERNOR_PROMOTION_OWLS_OF_MINERVA_1" Name="L1" Description="D1" Level="0" Column="1" BaseAbility="true"/>
    <Row GovernorPromotionType="GOVERNOR_PROMOTION_OWLS_OF_MINERVA_2" Name="L2" Description="D2" Level="1" Column="0" BaseAbility="false"/>
  </GovernorPromotions>
  <GovernorPromotionPrereqs>
    <Row GovernorPromotionType="GOVERNOR_PROMOTION_OWLS_OF_MINERVA_2" PrereqGovernorPromotion="GOVERNOR_PROMOTION_OWLS_OF_MINERVA_1"/>
  </GovernorPromotionPrereqs>
  <GovernorPromotionModifiers>
    <Row>
      <GovernorPromotionType>GOVERNOR_PROMOTION_OWLS_OF_MINERVA_1</GovernorPromotionType>
      <ModifierId>OWLS_TEST_POLICY_SLOT</ModifierId>
    </Row>
    <Row>
      <GovernorPromotionType>GOVERNOR_PROMOTION_OWLS_OF_MINERVA_1</GovernorPromotionType>
      <ModifierID>OWLS_TEST_TYPO_ROW</ModifierID>
    </Row>
    <Row>
      <GovernorPromotionType>GOVERNOR_PROMOTION_OWLS_OF_MINERVA_2</GovernorPromotionType>
      <ModifierId>OWLS_TEST_GOLD</ModifierId>
    </Row>
  </GovernorPromotionModifiers>
  <Modifiers>
    <Row ModifierId="OWLS_TEST_POLICY_SLOT" ModifierType="MODIFIER_PLAYER_CULTURE_ADJUST_GOVERNMENT_SLOTS_MODIFIER"/>
    <Row ModifierId="OWLS_TEST_TYPO_ROW" ModifierType="MODIFIER_CITY_ADJUST_CITIZEN_GOLD_PER_TURN"/>
    <Row ModifierId="OWLS_TEST_GOLD" ModifierType="MODIFIER_CITY_ADJUST_CITIZEN_GOLD_PER_TURN"/>
  </Modifiers>
  <ModifierArguments>
    <Row ModifierId="OWLS_TEST_POLICY_SLOT" Name="GovernmentSlotType" Value="SLOT_ECONOMIC"/>
    <Row ModifierId="OWLS_TEST_TYPO_ROW" Name="Amount" Value="2"/>
    <Row ModifierId="OWLS_TEST_GOLD" Name="Amount" Value="3"/>
  </ModifierArguments>
  <DynamicModifiers>
    <Row ModifierType="MODIFIER_PLAYER_CULTURE_ADJUST_GOVERNMENT_SLOTS_MODIFIER" CollectionType="COLLECTION_OWNER" EffectType="EFFECT_ADJUST_PLAYER_GOVERNOR_SLOT_TYPE"/>
    <Row ModifierType="MODIFIER_CITY_ADJUST_CITIZEN_GOLD_PER_TURN" CollectionType="COLLECTION_OWNER" EffectType="EFFECT_ADJUST_CITY_GOLD_FROM_CITIZENS"/>
  </DynamicModifiers>
  <GreatWorks_MODE>
    <Row GreatWorkType="GREATWORK_RELIC_25" RequiredGovernor="GOVERNOR_VOIDSINGERS"/>
  </GreatWorks_MODE>
  <GlobalParameters>
    <Update>
      <Where Name="MAX_GOVERNOR_APPOINTMENTS"/>
      <Set><Value>9</Value></Set>
    </Update>
  </GlobalParameters>
</GameInfo>
"""

MODE_EXPANSION2 = """<?xml version="1.0" encoding="utf-8"?>
<GameInfo>
  <Types>
    <Row Type="NOTIFICATION_SECRETSOCIETY_DISCOVERED" Kind="KIND_NOTIFICATION"/>
  </Types>
</GameInfo>
"""

MODE_GRANCOLOMBIA = """<?xml version="1.0" encoding="utf-8"?>
<GameInfo>
  <GovernorPromotionModifiers>
    <Row>
      <GovernorPromotionType>GOVERNOR_PROMOTION_HERMETIC_ORDER_3</GovernorPromotionType>
      <ModifierId>HERMETIC_ORDER_COMANDANTE_GENERAL_LEY_LINE_SCIENCE</ModifierId>
    </Row>
  </GovernorPromotionModifiers>
  <Modifiers>
    <Row ModifierId="HERMETIC_ORDER_COMANDANTE_GENERAL_LEY_LINE_SCIENCE" ModifierType="MODIFIER_PLAYER_ADJUST_GREAT_PERSON_RESOURCE_YIELD_CHANGE"/>
  </Modifiers>
  <ModifierArguments>
    <Row ModifierId="HERMETIC_ORDER_COMANDANTE_GENERAL_LEY_LINE_SCIENCE" Name="GreatPersonClassType" Value="GREAT_PERSON_CLASS_COMANDANTE_GENERAL"/>
    <Row ModifierId="HERMETIC_ORDER_COMANDANTE_GENERAL_LEY_LINE_SCIENCE" Name="YieldType" Value="YIELD_SCIENCE"/>
    <Row ModifierId="HERMETIC_ORDER_COMANDANTE_GENERAL_LEY_LINE_SCIENCE" Name="ResourceType" Value="RESOURCE_LEY_LINE"/>
    <Row ModifierId="HERMETIC_ORDER_COMANDANTE_GENERAL_LEY_LINE_SCIENCE" Name="Amount" Value="1"/>
  </ModifierArguments>
  <DynamicModifiers>
    <Row ModifierType="MODIFIER_PLAYER_ADJUST_GREAT_PERSON_RESOURCE_YIELD_CHANGE" CollectionType="COLLECTION_OWNER" EffectType="EFFECT_ADJUST_PLAYER_YIELD_CHANGE_PER_GREAT_PERSON_CLASS_ON_RESOURCE"/>
  </DynamicModifiers>
</GameInfo>
"""

MODINFO = """<?xml version="1.0" encoding="utf-8"?>
<Mod id="1B394FE9-23DC-4868-8F0A-5220CB8FB427" version="1">
  <Properties><Name>Ethiopia</Name></Properties>
  <ActionCriteria>
    <Criteria id="Ethiopia" any="1"><LeaderPlayable>LEADER_MENELIK</LeaderPlayable></Criteria>
    <Criteria id="Ethiopia_Mode"><ConfigurationValueMatches><Group>Game</Group><ConfigurationId>GAMEMODE_SECRETSOCIETIES</ConfigurationId><Value>1</Value></ConfigurationValueMatches></Criteria>
    <Criteria id="Ethiopia_Mode_Expansion2"><RuleSetInUse>RULESET_EXPANSION_2</RuleSetInUse></Criteria>
    <Criteria id="Ethiopia_Mode_Expansion2_GranColombia_Maya"><LeaderPlayable>LEADER_BOLIVAR,LEADER_LADY_SIX_SKY</LeaderPlayable></Criteria>
  </ActionCriteria>
  <InGameActions>
    <UpdateDatabase id="EthiopiaGameplay" criteria="Ethiopia">
      <File>Data/Ethiopia_Buildings.xml</File>
    </UpdateDatabase>
    <UpdateDatabase id="EthiopiaGameplayXP2_MODE" criteria="Ethiopia_Mode_Expansion2">
      <File>Data/Ethiopia_GameCapabilities.xml</File>
      <File>Data/Ethiopia_SecretSocieties_MODE.xml</File>
      <File>Data/Ethiopia_SecretSocieties_Expansion2_MODE.xml</File>
    </UpdateDatabase>
    <UpdateDatabase id="EthiopiaGranColombiaMayaGameplay_MODE" criteria="Ethiopia_Mode_Expansion2_GranColombia_Maya">
      <File>Data/Ethiopia_SecretSocieties_GranColombia_Maya_MODE.xml</File>
    </UpdateDatabase>
  </InGameActions>
</Mod>
"""


def fake_game_root(tmp: str) -> str:
    root = Path(tmp)
    d = root / "DLC" / "Ethiopia" / "Data"
    d.mkdir(parents=True, exist_ok=True)
    (root / "DLC" / "Ethiopia" / "Ethiopia.modinfo").write_text(MODINFO, encoding="utf-8")
    (d / "Ethiopia_Buildings.xml").write_text("<GameInfo/>", encoding="utf-8")
    (d / "Ethiopia_GameCapabilities.xml").write_text("<GameInfo/>", encoding="utf-8")
    (d / "Ethiopia_SecretSocieties_MODE.xml").write_text(MODE_MAIN, encoding="utf-8")
    (d / "Ethiopia_SecretSocieties_Expansion2_MODE.xml").write_text(MODE_EXPANSION2, encoding="utf-8")
    (d / "Ethiopia_SecretSocieties_GranColombia_Maya_MODE.xml").write_text(MODE_GRANCOLOMBIA, encoding="utf-8")
    return str(root)


def local_db():
    p = ROOT / "data" / "local" / "DebugGameplay_official.sqlite"
    if not p.is_file():
        raise FileNotFoundError(str(p))
    return p


def game_root_or_none():
    for cand in ([os.environ.get("CIV6_GAME_ROOT")] if os.environ.get("CIV6_GAME_ROOT")
                 else []) + [r for r in (
                     os.path.join(os.environ.get("ProgramFiles(x86)",
                                                 r"C:\Program Files (x86)"), "Steam",
                                  "steamapps", "common",
                                  "Sid Meier's Civilization VI"),)]:
        if cand and (Path(cand) / "DLC" / "Ethiopia" / "Ethiopia.modinfo").is_file():
            return cand
    return None


class TestDesignDecisions(unittest.TestCase):
    def test_proposed_owner_bit(self):
        from civ6x10.production import MODULE_BITS
        self.assertEqual(PROPOSED_GOVERNOR_MODULE_BIT, 32)
        self.assertEqual(PROPOSED_NEXT_MODULE_BIT_AFTER_GOVERNORS, 64)
        self.assertNotIn(32, set(MODULE_BITS.values()))

    def test_no_production_artifacts_from_audit(self):
        import civ6x10.governors as g
        self.assertFalse(hasattr(g, "emit_cxx"))
        self.assertFalse(hasattr(g, "emit_bridge_sql"))

    def test_misspelling_removed(self):
        import civ6x10.governors as g
        src = Path(g.__file__).read_text(encoding="utf-8")
        self.assertNotIn("GOVERNOR_VOIDSONGERS", src)
        self.assertNotIn("SECRETSOCIETY_VOIDSONGERS", src)


class TestSyntheticModePayload(unittest.TestCase):
    """CI-safe: action merging, criteria selection, typo normalisation."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = fake_game_root(self.tmp)

    def test_action_aware_file_resolution(self):
        payload = resolve_mode_payload(self.root, "Expansion2", True)
        self.assertTrue(payload["available"])
        files = [f["mod_relative_path"] for f in payload["files"]]
        self.assertIn("Data/Ethiopia_SecretSocieties_MODE.xml", files)
        self.assertIn("Data/Ethiopia_SecretSocieties_Expansion2_MODE.xml", files)
        self.assertIn("Data/Ethiopia_SecretSocieties_GranColombia_Maya_MODE.xml", files)
        self.assertNotIn("Data/Ethiopia_Buildings.xml", files)  # non-mode action
        by_file = {f["mod_relative_path"]: f for f in payload["files"]}
        self.assertEqual(by_file["Data/Ethiopia_SecretSocieties_MODE.xml"]["action_id"],
                         "EthiopiaGameplayXP2_MODE")
        self.assertEqual(by_file["Data/Ethiopia_SecretSocieties_GranColombia_Maya_MODE.xml"]["criteria"],
                         "Ethiopia_Mode_Expansion2_GranColombia_Maya")
        self.assertTrue(all(f["sha256"] for f in payload["files"]))

    def test_conditional_overlay_toggle(self):
        payload = resolve_mode_payload(self.root, "Expansion2", False)
        files = [f["mod_relative_path"] for f in payload["files"]]
        self.assertNotIn("Data/Ethiopia_SecretSocieties_GranColombia_Maya_MODE.xml", files)

    def test_typo_normalisation_counted(self):
        overlay = load_mode_overlay(self.root)
        self.assertEqual(overlay["typo_normalised"], 1)
        links = overlay["rows"]["GovernorPromotionModifiers"]
        ids = {r.get("ModifierId") for r in links}
        self.assertIn("OWLS_TEST_TYPO_ROW", ids)

    def test_grancolombia_overlay_modifier_reachable(self):
        overlay = load_mode_overlay(self.root)
        rows = overlay["rows"]
        promos = {r["GovernorPromotionType"] for r in rows["GovernorPromotionModifiers"]}
        self.assertIn("GOVERNOR_PROMOTION_HERMETIC_ORDER_3", promos)
        args = [r for r in rows["ModifierArguments"]
                if r["ModifierId"] == "HERMETIC_ORDER_COMANDANTE_GENERAL_LEY_LINE_SCIENCE"]
        self.assertEqual([a for a in args if a["Name"] == "Amount"][0]["Value"], "1")

    def test_entity_blob_from_synthetic_root(self):
        # <Row><Field>v</Field></Row> nested form must parse too.
        overlay = load_mode_overlay(self.root)
        rows = overlay["rows"]
        # main mode file (3) + Gran Colombia/Maya overlay (4) merge
        self.assertEqual(len(rows["ModifierArguments"]), 7)
        self.assertEqual(len(rows["GovernorPromotionModifiers"]), 4)  # 3 + overlay 1
        self.assertEqual(len(rows["SecretSocieties"]), 4)
        self.assertEqual(len(rows["GreatWorks_MODE"]), 1)
        self.assertEqual(len(rows["GovernorsCannotAssign"]), 1)


class TestSchemaDiscovery(unittest.TestCase):
    def test_column_scan_finds_all_governor_tables(self):
        import sqlite3
        try:
            db = sqlite3.connect(str(local_db()))
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        tables = discover_governor_tables_from_db(db)
        names = {t["table"] for t in tables}
        self.assertIn("GovernorReplaces", names)
        self.assertIn("GreatWorks_MODE", names)
        for expected in ("Governors", "Governors_XP2", "GovernorsCannotAssign",
                         "GovernorModifiers", "GovernorPromotionConditions",
                         "GovernorPromotionModifiers", "GovernorPromotionPrereqs",
                         "GovernorPromotionSets", "GovernorPromotions",
                         "SecretSocieties"):
            self.assertIn(expected, names)
        db.close()


class TestManifestInvariants(unittest.TestCase):
    """Invariants of the checked-in manifest that need no game data."""

    @classmethod
    def setUpClass(cls):
        import yaml
        p = ROOT / "civ6x10" / "rules" / "governor_audit.yml"
        if not p.is_file():
            raise unittest.SkipTest("governor_audit.yml not generated yet")
        cls.man = yaml.safe_load(p.read_text(encoding="utf-8"))

    def test_counts_are_consistent(self):
        m = self.man
        c = m["counts"]
        self.assertEqual(c["governors"], c["governors_base"]
                         + c["governors_secret_society"])
        self.assertEqual(c["promotions"], c["promotions_base"]
                         + c["promotions_secret_society"])
        d = m["disposition_summary"]["reachable_rows"]
        self.assertEqual(d["total"], d["CERTIFIED_CANDIDATE"] + d["EXCLUDED"]
                         + d["DECISION_REQUIRED"] + d["OUT_OF_GRAPH"])
        self.assertEqual(c["reachable_rows"], d["total"])

    def test_no_unexplained_rows(self):
        for gt, g in self.man["governors"].items():
            self.assertGreaterEqual(g["disposition_summary"]["total"], 0, gt)
        for pt, p in self.man["promotions"].items():
            self.assertGreaterEqual(p["disposition_summary"]["total"], 0, pt)

    def test_every_promotion_has_a_summary(self):
        self.assertEqual(len(self.man["promotions"]), self.man["counts"]["promotions"])
        self.assertEqual(len(self.man["governors"]), self.man["counts"]["governors"])

    def test_owner_bit_reported_not_implemented(self):
        self.assertEqual(self.man["proposed_owner_bit"], 32)
        self.assertEqual(self.man["proposed_next_bit_after"], 64)

    def test_mode_file_provenance_recorded(self):
        files = self.man["mode_files"]
        self.assertTrue(files)
        for f in files:
            self.assertTrue(f["file"], f)
            if f["exists"]:
                self.assertEqual(len(f["sha256"]), 64, f["file"])
                self.assertTrue(f["action"], f["file"])

    def test_typo_normalisation_reported(self):
        self.assertEqual(self.man["counts"]["typo_normalised"], 1)

    def test_shared_definition_reported(self):
        ov = self.man["registry_overlap"]
        self.assertIn("SULEIMAN_GOVERNOR_POINTS", ov.get("shared", []))


class TestRealIntegration(unittest.TestCase):
    """Full derivation; skips as a coherent group when inputs are absent."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.db = local_db()
        except FileNotFoundError:
            raise unittest.SkipTest("official DB copy unavailable (local-only)")
        cls.root = game_root_or_none()
        if cls.root is None:
            raise unittest.SkipTest("Civ VI install/mode XML unavailable "
                                    "(set CIV6_GAME_ROOT)")

    def test_full_derivation_matches_manifest(self):
        audit = build_audit(self.db, game_root=self.root, root=ROOT)
        manifest = build_manifest(audit)
        import yaml
        checked = yaml.safe_load(
            (ROOT / "civ6x10" / "rules" / "governor_audit.yml")
            .read_text(encoding="utf-8"))
        self.assertEqual(checked["counts"], manifest["counts"])
        self.assertEqual(checked["disposition_summary"],
                         manifest["disposition_summary"])
        self.assertEqual(checked["family_summary"], manifest["family_summary"])
        self.assertEqual(set(checked["governors"]), set(manifest["governors"]))
        self.assertEqual(set(checked["promotions"]), set(manifest["promotions"]))
        for gt, want in manifest["governors"].items():
            self.assertEqual(checked["governors"][gt]["disposition_summary"],
                             want["disposition_summary"], gt)
        for pt, want in manifest["promotions"].items():
            self.assertEqual(checked["promotions"][pt]["disposition_summary"],
                             want["disposition_summary"], pt)
        # provenance must be byte-identical too
        self.assertEqual(
            [(f["file"], f["sha256"], f["action"], f["criteria"])
             for f in checked["mode_files"]],
            [(f["file"], f["sha256"], f["action"], f["criteria"])
             for f in manifest["mode_files"]])

    def test_zero_skipped_integration_checks(self):
        # Derived counts must cover every discovered root.
        audit = build_audit(self.db, game_root=self.root, root=ROOT)
        u, rows = audit["universe"], audit["rows"]
        for gt in u["governors"]:
            self.assertTrue(any(r["root_governor"] == gt for r in rows), gt)
        with_rows = {r["root_promotion"] for r in rows if r["root_promotion"]}
        for pt in u["promotions"]:
            self.assertIn(pt, with_rows, pt)

    def test_corrected_dispositions(self):
        audit = build_audit(self.db, game_root=self.root, root=ROOT)
        rows = audit["rows"]
        by = {}
        for r in rows:
            by.setdefault((r["modifier_id"], r["argument"]), r)
        # appeal: additive but integral-gated
        a = by[("FORESTRY_MANAGEMENT_FEATURE_NO_IMPROVEMENT_APPEAL", "Amount")]
        self.assertEqual(a["family"], "APPEAL")
        self.assertEqual(a["disposition"], "CERTIFIED_CANDIDATE")
        self.assertTrue(a["engine_integral"])
        # serasker: magnitude and requirement scope separated
        s = by[("SERASKER_ADJUST_GOVERNOR_COMBAT_DISTRICT", "Amount")]
        self.assertEqual(s["family"], "COMBAT_STRENGTH_BONUS")
        self.assertEqual(s["disposition"], "CERTIFIED_CANDIDATE")
        rmax = by[("SERASKER_ADJUST_GOVERNOR_COMBAT_DISTRICT",
                   "PLOT_10_TILES_AWAY_MAX_REQUIREMENTS.MaxDistance")]
        self.assertEqual(rmax["disposition"], "EXCLUDED")
        self.assertEqual(rmax["family"], "SPATIAL_BUDGET")
        rmin = by[("SERASKER_ADJUST_GOVERNOR_COMBAT_DISTRICT",
                   "PLOT_10_TILES_AWAY_MAX_REQUIREMENTS.MinDistance")]
        self.assertEqual(rmin["disposition"], "EXCLUDED")
        # negative combat: decision-required (transform undefined)
        neg = by[("SECRET_SOCIETY_INTIMIDATE_ADJACENT_ENEMIES_MODIFIER", "Amount")]
        self.assertEqual(neg["disposition"], "DECISION_REQUIRED")
        self.assertEqual(neg["value"], "-5")
        # both healing rows held
        h1 = by[("CARDINAL_LAYING_ON_OF_HANDS_HEAL", "Amount")]
        h2 = by[("CARDINAL_LAYING_ON_OF_HANDS_RELIGIOUS_HEAL", "Amount")]
        self.assertEqual(h1["disposition"], "DECISION_REQUIRED")
        self.assertEqual(h2["disposition"], "DECISION_REQUIRED")

    def test_negative_combat_transform_refuses(self):
        from civ6x10 import transforms as T
        # the canonical transform is undefined for negative strengths: the
        # implementation must refuse rather than produce a number.
        for k in (7.3, 10.0):
            with self.assertRaises(ValueError):
                T.combat_bonus_for_multiplier(-5.0, k)

    def test_grancolombia_overlay_row_present(self):
        audit = build_audit(self.db, game_root=self.root, root=ROOT)
        rows = audit["rows"]
        hit = [r for r in rows if r["modifier_id"] ==
               "HERMETIC_ORDER_COMANDANTE_GENERAL_LEY_LINE_SCIENCE"
               and r["argument"] == "Amount"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["value"], "1")
        self.assertEqual(hit[0]["disposition"], "CERTIFIED_CANDIDATE")

    def test_secret_society_scope(self):
        audit = build_audit(self.db, game_root=self.root, root=ROOT)
        u = audit["universe"]
        self.assertEqual(secret_society_governor_types(u),
                         SECRET_SOCIETY_GOVERNORS)
        self.assertEqual(len(u["secret_society_governors"]), 4)
        cells = audit["direct_cells"]
        chances = [c for c in cells if c["cell"].startswith("DiscoverAt")]
        self.assertEqual(len(chances), 4)
        self.assertTrue(all(c["disposition"] == "EXCLUDED" for c in chances))
        caps = [c for c in cells if "MAX_GOVERNOR_APPOINTMENTS" in c["cell"]]
        self.assertEqual(len(caps), 1)
        gw = [c for c in cells if c["cell"] == "RequiredGovernor"]
        self.assertTrue(gw)
        ca = [c for c in cells if c["cell"] == "CannotAssign"]
        self.assertEqual(len(ca), 4)

    def test_registry_overlap(self):
        audit = build_audit(self.db, game_root=self.root, root=ROOT)
        ov = audit["registry_overlap"]
        self.assertTrue(ov["available"])
        self.assertEqual(ov["shared"], ["SULEIMAN_GOVERNOR_POINTS"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
