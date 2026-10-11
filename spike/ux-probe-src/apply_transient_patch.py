"""Transient scratch-build patch for the UX config-variant probe DLL.

Applies (all guarded by X10_UX_PROBE, all reverted by the build script):
1. vcxproj Release|x64: append X10_UX_PROBE to PreprocessorDefinitions.
2. vcxproj: add X10UxProbe.cpp to ClCompile items.
3. X10Lifecycle.cpp: file-scope forward declaration (after includes).
4. X10Lifecycle.cpp: UxProbeRead() call after the Populate EXIT log.

Usage: apply_transient_patch.py <fork-root>. Fails loudly unless every
anchor matches exactly once. X10UxProbe.cpp itself is copied by the caller.
"""
import io
import sys

DECL = '''
#ifdef X10_UX_PROBE
// SCRATCH ONLY (Phase 7C.1): forward declaration for the logging-only
// UX config-variant probe (defined in X10UxProbe.cpp, same guard).
// Production builds never see this declaration.
namespace X10Config { void UxProbeRead(); }
#endif
'''

CALL = '''
#ifdef X10_UX_PROBE
            // SCRATCH ONLY (Phase 7C.1): logging reads of X10_UX_* setup
            // keys for variant evidence. Results discarded; no arming, no
            // writes, no module-state change. Production builds (define
            // absent) compile exactly as before this block existed.
            X10Config::UxProbeRead();
#endif
'''


def main(fork: str) -> int:
    vcx = fork + r'\CivilizationVI_CommunityExtension.vcxproj'
    t = io.open(vcx, encoding='utf-8').read()
    old_def = ('NDEBUG;_CONSOLE;ASMJIT_STATIC;ASMJIT_NO_AARCH64;'
               '%(PreprocessorDefinitions)')
    assert t.count(old_def) == 1, 'Release|x64 defines anchor'
    t = t.replace(old_def,
                  old_def.replace('%(PreprocessorDefinitions)',
                                  'X10_UX_PROBE;%(PreprocessorDefinitions)'), 1)
    old_cc = '<ClCompile Include="X10Write.cpp" />'
    assert t.count(old_cc) == 1, 'ClCompile anchor'
    t = t.replace(old_cc,
                  old_cc + '\n    <ClCompile Include="X10UxProbe.cpp" />', 1)
    io.open(vcx, 'w', encoding='utf-8', newline='').write(t)

    lc = fork + r'\X10Lifecycle.cpp'
    s = io.open(lc, encoding='utf-8').read()
    a1 = '#include "X10Compat.h"'
    assert s.count(a1) == 1, 'include anchor'
    s = s.replace(a1, a1 + '\n' + DECL, 1)
    a2 = 'X10Write::SkippedThisPopulate());'
    assert s.count(a2) == 1, 'exit-log anchor'
    s = s.replace(a2, a2 + '\n' + CALL, 1)
    io.open(lc, 'w', encoding='utf-8', newline='').write(s)
    print('transient patch applied')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
