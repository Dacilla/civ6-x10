import io
p = 'civ6x10/bridge.py'
t = io.open(p, encoding='utf-8').read()
old_comment = """    # WHEN encodes the identical baseline predicate against the arriving row;
    # zeroing stays conditional on helper existence. Same fail-closed rules,
    # just deferred. Trigger names are deterministic (X10_TRG_<id-suffix>)."""
new_comment = """    # WHEN encodes the identical baseline predicate against the arriving row.
    # Phase 8B: no zeroing (non-destructive delta) -- the helper starts inert
    # (Amount=0) and the direct cell is left intact. Same fail-closed rules,
    # just deferred. Trigger names are deterministic (X10_TRG_<id-suffix>)."""
assert t.count(old_comment) == 1, t.count(old_comment)
t = t.replace(old_comment, new_comment, 1)
old_zero = """    body = _helper_inserts_trigger(spec, hid, row, keys)
    zero = (
        "  UPDATE %s SET %s = 0 WHERE rowid = NEW.rowid\\n"
        "    AND EXISTS (SELECT 1 FROM Modifiers WHERE ModifierId = '%s');"
        % (row["source_table"], row["value_column"], hid))
    diag = "\\n".join("  " + ln for ln in _diag_trigger_update(
        hid, row, "trigger").split("\\n"))
    return (
        "CREATE TRIGGER IF NOT EXISTS %s\\n"
        "AFTER INSERT ON %s\\nFOR EACH ROW\\nWHEN %s\\nBEGIN\\n%s\\n%s\\n%s\\nEND;"
        % (tname, row["source_table"], _new_baseline_pred(row, keys),
           "\\n".join(body), zero, diag))"""
new_zero = """    body = _helper_inserts_trigger(spec, hid, row, keys)
    diag = "\\n".join("  " + ln for ln in _diag_trigger_update(
        hid, row, "trigger").split("\\n"))
    return (
        "CREATE TRIGGER IF NOT EXISTS %s\\n"
        "AFTER INSERT ON %s\\nFOR EACH ROW\\nWHEN %s\\nBEGIN\\n%s\\n%s\\nEND;"
        % (tname, row["source_table"], _new_baseline_pred(row, keys),
           "\\n".join(body), diag))"""
assert t.count(old_zero) == 1, t.count(old_zero)
t = t.replace(old_zero, new_zero, 1)
old_doc = '''    """Guarded helper-creation + direct-zeroing SQL (deterministic).

    Two execution paths share identical predicates:
    - immediate: rows present when the bridge runs (base/expansion content);
    - deferred triggers: rows inserted AFTER the bridge runs (proven live:
      DLC-pack rows arrive later). WHEN encodes the baseline; zeroing stays
      conditional on helper existence. A diagnostics table records per-cell
      state for the local-only probe dump.
    """'''
new_doc = '''    """Guarded helper-creation SQL (deterministic, non-destructive).

    Two execution paths share identical predicates:
    - immediate: rows present when the bridge runs (base/expansion content);
    - deferred triggers: rows inserted AFTER the bridge runs (proven live:
      DLC-pack rows arrive later). WHEN encodes the baseline. Phase 8B: the
      direct cell is NEVER zeroed (vanilla UI keeps reading the truthful
      official value); the helper starts inert (Amount=0) and the native
      DELTA kind contributes official*(k-1). A diagnostics table records
      per-cell state for the local-only probe dump.
    """'''
assert t.count(old_doc) == 1, t.count(old_doc)
t = t.replace(old_doc, new_doc, 1)
old_hdr = '''        "-- Each helper is created ONLY when the direct cell still holds its",
        "-- audited official value, and each direct cell is zeroed ONLY when",
        "-- it holds that value AND its helper exists. Drift leaves vanilla",
        "-- untouched and the dormant registry row can never match at runtime.",'''
new_hdr = '''        "-- Each helper is created ONLY when the direct cell still holds its",
        "-- audited official value. The direct cell is NEVER zeroed (Phase 8B",
        "-- non-destructive delta): drift leaves vanilla untouched and the",
        "-- dormant registry row can never match at runtime.",'''
assert t.count(old_hdr) == 1, t.count(old_hdr)
t = t.replace(old_hdr, new_hdr, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('bridge delta rewrite ok')
