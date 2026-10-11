// X10 UX config-variant probe (SCRATCH ONLY, Phase 7C.1).
//
// Entire functional body is compiled ONLY under X10_UX_PROBE. Production
// builds (define absent) see an empty translation unit: no symbols, no
// behavior change. Reads a fixed list of X10_UX_* setup keys through the
// proven TryGetMultiplier path purely for its variant-evidence logging
// (type/id/flags/numeric, or undecodable-variant + raw payload bytes).
// Results are discarded: this probe never arms transforms, never writes
// definitions, never changes module state.
#ifdef X10_UX_PROBE

namespace X10Config {

bool TryGetMultiplier(const char* key, double& out, double& kErrOut);

void UxProbeRead() {
    static const char* kKeys[] = {
        "X10_UX_PRESET",
        "X10_UX_CUSTOM",
        "X10_UX_BOOL_TRAITS",
        "X10_UX_BOOL_POLICIES",
        "X10_UX_BOOL_GOVERNMENTS",
        "X10_UX_BOOL_PANTHEONS",
        "X10_UX_BOOL_WONDERS",
        "X10_UX_BOOL_GOVERNORS",
        "X10_UX_BOOL_SUZERAIN",
        "X10_MULTIPLIER",  // control: absent in the probe run
    };
    for (size_t i = 0; i < sizeof(kKeys) / sizeof(kKeys[0]); i++) {
        double out = 0;
        double err = 0;
        (void)TryGetMultiplier(kKeys[i], out, err);
    }
}

}  // namespace X10Config

#endif  // X10_UX_PROBE
