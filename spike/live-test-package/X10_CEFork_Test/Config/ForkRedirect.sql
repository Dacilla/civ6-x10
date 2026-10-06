-- GameCore redirect for the local X10 lifecycle fork.
-- Mirrors the known-working installed Community Extension configuration:
-- the game loads Binaries/Win64/GameCore_XP2_CE_FinalRelease.dll from this
-- mod folder instead of the stock GameCore.
UPDATE GameCores
SET
    PackageId = '308d6fa9-0fb8-4153-8376-5a5a5a1b5d2d',
    DllPrefix = 'GameCore_XP2_CE'
WHERE
    GameCore = 'Expansion2';
