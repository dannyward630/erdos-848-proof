param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Upstream = "https://github.com/crabsatellite/erdos-848-squarefree-product.git"
$Revision = "ede0151a35c86b6395cf67dd034811d22a92c7ba"
$RootTree = "5b1253061e916513036d30d8275c9aeaddb0e771"
$LeanTree = "6b9794fafddd3e7780c6a10a442f2e4e9dc73c1a"
$ProblemCoreSourceSha256 = "3cc1f264149eaf99e18a04c8f57e4c6850c8571d0cb5b1de0fefdec087d5cfec"
$LeanToolchainSha256 = "ce4c4e3d87434b9663f46de25ce34b48a0cf0d392e0a320a0787b4674a2d7b61"
$LakeManifestSha256 = "e016cb20d7f2f3b2bef02393f4b468fdd4f8fdeba9784aabb39e2889a87b5d4c"
$LakefileSha256 = "7479e2c461de9c48bcf32fc210ee2ce56d6d1a485c0a0d49d17f934082074912"
$LeanZipName = "lean-4.30.0-rc2-windows.zip"
$LeanZipSha256 = "cb0688631203ac7832e447a5791e51e88db938b6038ff788eea73491619988b2"
$LeanZipUrl = "https://github.com/leanprover/lean4/releases/download/v4.30.0-rc2/$LeanZipName"
$ShardName = "erdos848-olean-cache-lean-4.30.0-rc2-windows-x86_64-e0dd18260bd4-part-075-of-075.zip"
$ShardSha256 = "05691d7a716da25b1e42b6bdf20df7246caefde7976f8eefa26f4643d473a37a"
$ShardUrl = "https://github.com/crabsatellite/erdos-848-squarefree-product/releases/download/v1.0.5-kernel/$ShardName"
$ExpectedOleanSha256 = "324f23465ac359c47291515bb3faaed5be7046341ad580bb46613eec81e47a4d"
$ExpectedOleanBytes = [uint64]95664

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )

    Write-Host "RUN $Description"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

function Invoke-CurlDownload {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    & curl.exe `
        --location `
        --fail `
        --silent `
        --show-error `
        --retry 5 `
        --retry-delay 5 `
        --retry-all-errors `
        --output $Destination `
        $Url
    if ($LASTEXITCODE -ne 0) {
        throw "curl failed with exit code $LASTEXITCODE for $Url"
    }
}

function Assert-Sha256 {
    param(
        [Parameter(Mandatory = $true)][string]$LiteralPath,
        [Parameter(Mandatory = $true)][string]$Expected
    )

    $observed = (Get-FileHash -LiteralPath $LiteralPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($observed -cne $Expected) {
        throw "SHA-256 mismatch for ${LiteralPath}: $observed"
    }
    return $observed
}

if ($env:RUNNER_OS -cne "Windows" -or $env:RUNNER_ARCH -cne "X64") {
    throw "pilot requires Windows x86-64"
}

foreach ($name in @("LEAN_PATH", "LEAN_SRC_PATH", "LEAN_PKG_PATH")) {
    Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
}

$scratch = [IO.Path]::GetFullPath((Join-Path $env:RUNNER_TEMP "e848-problem-core-pilot"))
$outputFull = [IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $scratch) {
    throw "scratch path unexpectedly exists: $scratch"
}
[void](New-Item -ItemType Directory -Path $scratch)

$sourceRoot = Join-Path $scratch "source"
Invoke-Checked -Description "partial clone" -Command {
    & git clone --filter=blob:none --no-checkout $Upstream $sourceRoot
}
Invoke-Checked -Description "initialize non-cone sparse checkout" -Command {
    & git -C $sourceRoot sparse-checkout init --no-cone
}
$sparsePaths = @(
    "/lean4/lean-toolchain",
    "/lean4/lakefile.toml",
    "/lean4/lake-manifest.json",
    "/lean4/Erdos848/ProblemCore.lean"
)
Write-Host "RUN set exact sparse paths"
$sparsePaths | & git -C $sourceRoot sparse-checkout set --stdin
if ($LASTEXITCODE -ne 0) {
    throw "sparse-checkout set failed with exit code $LASTEXITCODE"
}
Invoke-Checked -Description "checkout pinned ART-006 revision" -Command {
    & git -C $sourceRoot checkout --detach $Revision
}

$observedRevision = (& git -C $sourceRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $observedRevision -cne $Revision) {
    throw "upstream revision mismatch: $observedRevision"
}
$observedRootTree = (& git -C $sourceRoot rev-parse "HEAD^{tree}").Trim()
if ($LASTEXITCODE -ne 0 -or $observedRootTree -cne $RootTree) {
    throw "upstream root tree mismatch: $observedRootTree"
}
$observedLeanTree = (& git -C $sourceRoot rev-parse "HEAD:lean4").Trim()
if ($LASTEXITCODE -ne 0 -or $observedLeanTree -cne $LeanTree) {
    throw "upstream Lean tree mismatch: $observedLeanTree"
}
$dirty = @(& git -C $sourceRoot status --porcelain)
if ($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0) {
    throw "sparse source checkout is dirty"
}

$lean4 = Join-Path $sourceRoot "lean4"
$problemCore = Join-Path $lean4 "Erdos848/ProblemCore.lean"
[void](Assert-Sha256 -LiteralPath $problemCore -Expected $ProblemCoreSourceSha256)
[void](Assert-Sha256 -LiteralPath (Join-Path $lean4 "lean-toolchain") -Expected $LeanToolchainSha256)
[void](Assert-Sha256 -LiteralPath (Join-Path $lean4 "lake-manifest.json") -Expected $LakeManifestSha256)
[void](Assert-Sha256 -LiteralPath (Join-Path $lean4 "lakefile.toml") -Expected $LakefileSha256)

$runtimeZip = Join-Path $scratch $LeanZipName
$runtimeRoot = Join-Path $scratch "lean-runtime"
[void](New-Item -ItemType Directory -Path $runtimeRoot)
Invoke-CurlDownload -Url $LeanZipUrl -Destination $runtimeZip
[void](Assert-Sha256 -LiteralPath $runtimeZip -Expected $LeanZipSha256)
Invoke-Checked -Description "extract pinned Lean runtime" -Command {
    & tar.exe -xf $runtimeZip -C $runtimeRoot
}
Remove-Item -LiteralPath $runtimeZip -Force

$leanExe = @(Get-ChildItem -LiteralPath $runtimeRoot -Recurse -File -Filter "lean.exe" |
    Where-Object { $_.Directory.Name -ceq "bin" })
$lakeExe = @(Get-ChildItem -LiteralPath $runtimeRoot -Recurse -File -Filter "lake.exe" |
    Where-Object { $_.Directory.Name -ceq "bin" })
if ($leanExe.Count -ne 1 -or $lakeExe.Count -ne 1) {
    throw "could not resolve exactly one lean.exe and lake.exe"
}
$leanExe = $leanExe[0].FullName
$lakeExe = $lakeExe[0].FullName
$runtimeBin = Split-Path -Parent $leanExe
$env:PATH = "$runtimeBin;$env:PATH"
$leanVersion = (& $leanExe --version | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "lean --version failed"
}
if ($leanVersion -notmatch "4[.]30[.]0" -or $leanVersion -notmatch "3dc1a088") {
    throw "unexpected Lean version: $leanVersion"
}

Push-Location $lean4
try {
    Invoke-Checked -Description "pinned mathlib cache bootstrap" -Command {
        & $lakeExe exe cache get
    }
    $projectOleansBefore = @(Get-ChildItem -LiteralPath (Join-Path $lean4 ".lake") `
        -Recurse -File -Filter "*.olean" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -like "*\.lake\build\lib\lean\Erdos848\*" })
    if ($projectOleansBefore.Count -ne 0) {
        throw "project OLean existed before source pilot"
    }

    # The published cache was produced by the controlled builder, not by a
    # default Lean invocation.  Lean serializes some command-line options into
    # OLean, so probe the exact builder command at every historically used
    # memory ceiling.  Repeat the 24,576-MiB case at a second output path to
    # test path independence separately from cache equality.
    $variantSpecs = @(
        [ordered]@{ label = "memory-6144"; memory_mib = 6144 },
        [ordered]@{ label = "memory-12288"; memory_mib = 12288 },
        [ordered]@{ label = "memory-15360"; memory_mib = 15360 },
        [ordered]@{ label = "memory-24576-a"; memory_mib = 24576 },
        [ordered]@{ label = "memory-24576-b"; memory_mib = 24576 },
        [ordered]@{ label = "memory-32768"; memory_mib = 32768 }
    )
    $compiledVariants = @()
    foreach ($spec in $variantSpecs) {
        $sourceOlean = Join-Path $scratch "ProblemCore.$($spec.label).olean"
        $leanArgs = @(
            "env", "lean", "--trust=0", "-q", "-M",
            [string]$spec.memory_mib,
            "-D", "compiler.postponeCompile=true",
            "-o", $sourceOlean,
            "Erdos848/ProblemCore.lean"
        )
        Invoke-Checked -Description "compile ProblemCore.lean $($spec.label)" -Command {
            & $lakeExe @leanArgs
        }
        $info = Get-Item -LiteralPath $sourceOlean
        $hash = (Get-FileHash -LiteralPath $sourceOlean -Algorithm SHA256).Hash.ToLowerInvariant()
        $compiledVariants += [ordered]@{
            label = [string]$spec.label
            memory_mib = [int]$spec.memory_mib
            output_path = [IO.Path]::GetFileName($sourceOlean)
            output_bytes = [uint64]$info.Length
            output_sha256 = $hash
        }
    }
}
finally {
    Pop-Location
}

$shardPath = Join-Path $scratch $ShardName
$shardExtract = Join-Path $scratch "shard-075"
[void](New-Item -ItemType Directory -Path $shardExtract)
Invoke-CurlDownload -Url $ShardUrl -Destination $shardPath
[void](Assert-Sha256 -LiteralPath $shardPath -Expected $ShardSha256)
Invoke-Checked -Description "extract authenticated shard 075" -Command {
    & tar.exe -xf $shardPath -C $shardExtract
}
$releaseOlean = Join-Path $shardExtract "lean4/.lake/build/lib/lean/Erdos848/ProblemCore.olean"
$releaseInfo = Get-Item -LiteralPath $releaseOlean
$releaseHash = (Get-FileHash -LiteralPath $releaseOlean -Algorithm SHA256).Hash.ToLowerInvariant()
if ([uint64]$releaseInfo.Length -ne $ExpectedOleanBytes -or $releaseHash -cne $ExpectedOleanSha256) {
    throw "authenticated release ProblemCore.olean does not match its manifest entry"
}

$releaseBytes = [IO.File]::ReadAllBytes($releaseOlean)
foreach ($variant in $compiledVariants) {
    $variantPath = Join-Path $scratch $variant.output_path
    $variantBytes = [IO.File]::ReadAllBytes($variantPath)
    $variant["byte_for_byte_equal"] = [System.Collections.StructuralComparisons]::StructuralEqualityComparer.Equals(
        $variantBytes,
        $releaseBytes
    )
    $variant["matches_release_manifest"] = (
        [uint64]$variant.output_bytes -eq $ExpectedOleanBytes -and
        $variant.output_sha256 -ceq $ExpectedOleanSha256 -and
        $variant.byte_for_byte_equal
    )
}
$sameCapA = $compiledVariants | Where-Object { $_.label -ceq "memory-24576-a" }
$sameCapB = $compiledVariants | Where-Object { $_.label -ceq "memory-24576-b" }
$sameCapPathIndependent = (
    $sameCapA.output_bytes -eq $sameCapB.output_bytes -and
    $sameCapA.output_sha256 -ceq $sameCapB.output_sha256
)
$matchingVariants = @($compiledVariants | Where-Object { $_.matches_release_manifest })
$matchesExpected = $matchingVariants.Count -gt 0

$report = [ordered]@{
    schema_version = 2
    github = [ordered]@{
        repository = [string]$env:GITHUB_REPOSITORY
        run_id = [string]$env:GITHUB_RUN_ID
        run_attempt = [string]$env:GITHUB_RUN_ATTEMPT
        sha = [string]$env:GITHUB_SHA
    }
    upstream = [ordered]@{
        revision = $observedRevision
        root_tree = $observedRootTree
        lean_tree = $observedLeanTree
        problem_core_source_sha256 = $ProblemCoreSourceSha256
    }
    toolchain = [ordered]@{
        release_asset = $LeanZipName
        release_asset_sha256 = $LeanZipSha256
        lean_version = $leanVersion
        lake_manifest_sha256 = $LakeManifestSha256
        mathlib_revision = "54e71fa9173471d591658f5380c46aaf050bbaae"
    }
    expected_release_olean = [ordered]@{
        archive = $ShardName
        archive_sha256 = $ShardSha256
        bytes = $ExpectedOleanBytes
        sha256 = $ExpectedOleanSha256
    }
    source_compilation = [ordered]@{
        exact_builder_arguments = @(
            "--trust=0", "-q", "-M", "<memory_mib>",
            "-D", "compiler.postponeCompile=true"
        )
        variants = $compiledVariants
        release_output_bytes = [uint64]$releaseInfo.Length
        release_output_sha256 = $releaseHash
        matching_variant_labels = @($matchingVariants | ForEach-Object { $_.label })
        repeated_24576_path_independent = $sameCapPathIndependent
        matches_release_manifest = $matchesExpected
    }
}

$outputParent = Split-Path -Parent $outputFull
if (-not (Test-Path -LiteralPath $outputParent)) {
    [void](New-Item -ItemType Directory -Path $outputParent)
}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outputFull -Encoding utf8NoBOM
Write-Host "REPORT $outputFull"
foreach ($variant in $compiledVariants) {
    Write-Host "variant=$($variant.label) memory_mib=$($variant.memory_mib) bytes=$($variant.output_bytes) sha256=$($variant.output_sha256) release_equal=$($variant.byte_for_byte_equal)"
}
Write-Host "release_olean_bytes=$($releaseInfo.Length)"
Write-Host "release_olean_sha256=$releaseHash"
Write-Host "repeated_24576_path_independent=$sameCapPathIndependent"
Write-Host "matches_release_manifest=$matchesExpected"
if ($matchesExpected) {
    Write-Host "PROBLEMCORE SOURCE-CACHE DETERMINISM PILOT PASSED"
}
else {
    Write-Host "PROBLEMCORE SOURCE-CACHE DETERMINISM PILOT MISMATCH"
}
