-- GameCore redirect for the X10 CE Engine (production).
-- Mirrors the known-working Community Extension configuration: the game
-- loads Binaries/Win64/GameCore_XP2_CE_FinalRelease.dll from this mod
-- folder instead of the stock GameCore.
UPDATE GameCores
SET
    PackageId = '397f2070-dfde-4124-88ce-e34249fc8190',
    DllPrefix = 'GameCore_XP2_CE'
WHERE
    GameCore = 'Expansion2';
