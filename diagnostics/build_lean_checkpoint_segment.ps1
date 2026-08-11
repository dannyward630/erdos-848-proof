param(
    [Parameter(Mandatory = $true)][string]$SourceRoot,
    [Parameter(Mandatory = $true)][string]$PlanPath,
    [Parameter(Mandatory = $true)][string]$LockPath,
    [Parameter(Mandatory = $true)][int]$SegmentIndex,
    [Parameter(Mandatory = $true)][string]$OutputRoot,
    [string[]]$ParentRoot = @(),
    [int]$MemoryMiB = 24576
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

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

function Resolve-SafeDirectory {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)
    $full = [IO.Path]::GetFullPath($LiteralPath)
    if (-not (Test-Path -LiteralPath $full -PathType Container)) {
        throw "directory does not exist: $full"
    }
    $item = Get-Item -LiteralPath $full -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "directory must not be a reparse point: $full"
    }
    return $full
}

function Invoke-CurlDownload {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Destination
    )
    & curl.exe --location --fail --silent --show-error --retry 5 `
        --retry-delay 5 --retry-all-errors --output $Destination $Url
    if ($LASTEXITCODE -ne 0) {
        throw "curl failed with exit code $LASTEXITCODE for $Url"
    }
}

function Get-Erdos848Oleans {
    param([Parameter(Mandatory = $true)][string]$Lean4Root)
    $lakeRoot = Join-Path $Lean4Root ".lake"
    if (-not (Test-Path -LiteralPath $lakeRoot)) {
        return @()
    }
    return @(Get-ChildItem -LiteralPath $lakeRoot -Recurse -File `
        -Filter "*.olean" -ErrorAction Stop | Where-Object {
            $_.FullName -match "[\\/]Erdos848[\\/]"
        })
}

if ($env:RUNNER_OS -cne "Windows" -or $env:RUNNER_ARCH -cne "X64") {
    throw "checkpoint segment builder requires Windows x86-64"
}
if ($MemoryMiB -lt 1024) {
    throw "MemoryMiB is implausibly small"
}
foreach ($name in @("LEAN_PATH", "LEAN_SRC_PATH", "LEAN_PKG_PATH")) {
    Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
}

$repo = Resolve-SafeDirectory -LiteralPath $PSScriptRoot
$repo = Split-Path -Parent $repo
$source = Resolve-SafeDirectory -LiteralPath $SourceRoot
$plan = [IO.Path]::GetFullPath($PlanPath)
$lock = [IO.Path]::GetFullPath($LockPath)
$output = [IO.Path]::GetFullPath($OutputRoot)
if (Test-Path -LiteralPath $output) {
    throw "output root must not already exist: $output"
}
[void](New-Item -ItemType Directory -Path $output)
$outputItem = Get-Item -LiteralPath $output -Force
if (($outputItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw "output root must not be a reparse point"
}

$python = (Get-Command python -CommandType Application -ErrorAction Stop).Source
$planner = Join-Path $repo "diagnostics/lean_checkpoint_plan.py"
Invoke-Checked -Description "authenticate canonical plan and source" -Command {
    & $python -B $planner verify-plan --plan $plan --source-root $source --lock $lock
}

$planObject = Get-Content -LiteralPath $plan -Raw | ConvertFrom-Json
if ($SegmentIndex -lt 0 -or $SegmentIndex -ge $planObject.segments.Count) {
    throw "segment index is outside the plan"
}
$segment = $planObject.segments[$SegmentIndex]
if ($segment.index -ne $SegmentIndex) {
    throw "segment index disagrees with canonical position"
}
$expectedParents = @($segment.parents)
if ($ParentRoot.Count -ne $expectedParents.Count) {
    throw "expected $($expectedParents.Count) parent roots, got $($ParentRoot.Count)"
}

$lean4 = Join-Path $source "lean4"
$runtimeZipName = "lean-4.30.0-rc2-windows.zip"
$runtimeZipSha256 = "cb0688631203ac7832e447a5791e51e88db938b6038ff788eea73491619988b2"
$runtimeZipUrl = "https://github.com/leanprover/lean4/releases/download/v4.30.0-rc2/$runtimeZipName"
$runtimeBase = Join-Path $env:RUNNER_TEMP "e848-checkpoint-runtime-$SegmentIndex"
if (Test-Path -LiteralPath $runtimeBase) {
    throw "runtime path unexpectedly exists: $runtimeBase"
}
[void](New-Item -ItemType Directory -Path $runtimeBase)
$runtimeZip = Join-Path $runtimeBase $runtimeZipName
$runtimeRoot = Join-Path $runtimeBase "runtime"
[void](New-Item -ItemType Directory -Path $runtimeRoot)
Invoke-CurlDownload -Url $runtimeZipUrl -Destination $runtimeZip
$runtimeDigest = (Get-FileHash -LiteralPath $runtimeZip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($runtimeDigest -cne $runtimeZipSha256) {
    throw "pinned Lean runtime SHA-256 mismatch: $runtimeDigest"
}
Invoke-Checked -Description "extract pinned Lean runtime" -Command {
    & tar.exe -xf $runtimeZip -C $runtimeRoot
}
Remove-Item -LiteralPath $runtimeZip -Force
$leanCandidates = @(Get-ChildItem -LiteralPath $runtimeRoot -Recurse -File `
    -Filter "lean.exe" | Where-Object { $_.Directory.Name -ceq "bin" })
$lakeCandidates = @(Get-ChildItem -LiteralPath $runtimeRoot -Recurse -File `
    -Filter "lake.exe" | Where-Object { $_.Directory.Name -ceq "bin" })
if ($leanCandidates.Count -ne 1 -or $lakeCandidates.Count -ne 1) {
    throw "could not resolve exactly one lean.exe and lake.exe from pinned runtime"
}
$lean = $leanCandidates[0].FullName
$lake = $lakeCandidates[0].FullName
$env:PATH = "$(Split-Path -Parent $lean);$env:PATH"
$leanVersion = (& $lean --version | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $leanVersion -notmatch "4[.]30[.]0" -or
    $leanVersion -notmatch "3dc1a088") {
    throw "unexpected Lean runtime: $leanVersion"
}

Push-Location $lean4
try {
    Invoke-Checked -Description "bootstrap pinned third-party cache" -Command {
        & $lake exe cache get
    }

    $before = @(Get-Erdos848Oleans -Lean4Root $lean4)
    if ($before.Count -ne 0) {
        throw "segment did not start from genesis: found $($before.Count) project OLeans"
    }

    $expectedImported = [System.Collections.Generic.HashSet[string]]::new(
        [StringComparer]::Ordinal)
    $expectedImportedHashes = [System.Collections.Generic.Dictionary[string,string]]::new(
        [StringComparer]::Ordinal)
    for ($position = 0; $position -lt $ParentRoot.Count; $position++) {
        $parent = Resolve-SafeDirectory -LiteralPath $ParentRoot[$position]
        $parentArgs = @(
            "-B", $planner, "verify-receipt",
            "--plan", $plan,
            "--asset-root", $parent,
            "--segment-index", [string]$expectedParents[$position]
        )
        Invoke-Checked -Description "verify parent segment $($expectedParents[$position])" `
            -Command { & $python @parentArgs }
        $parentReceipt = Get-Content -LiteralPath (Join-Path $parent "receipt.json") `
            -Raw | ConvertFrom-Json
        foreach ($module in @($parentReceipt.modules)) {
            $relative = [string]$module.olean_path
            if (-not $relative.StartsWith("oleans/", [StringComparison]::Ordinal)) {
                throw "parent OLean path escaped its asset root"
            }
            $sourceOlean = Join-Path $parent $relative
            $moduleRelative = $relative.Substring("oleans/".Length)
            $destination = Join-Path (Join-Path $lean4 ".lake/build/lib/lean") $moduleRelative
            [void](New-Item -ItemType Directory -Path (Split-Path -Parent $destination) `
                -Force)
            Copy-Item -LiteralPath $sourceOlean -Destination $destination
            $destination = [IO.Path]::GetFullPath($destination)
            if (-not $expectedImported.Add($destination)) {
                throw "duplicate parent OLean destination: $destination"
            }
            $expectedHash = [string]$module.olean_sha256
            $copiedHash = (Get-FileHash -LiteralPath $destination `
                -Algorithm SHA256).Hash.ToLowerInvariant()
            $copiedBytes = (Get-Item -LiteralPath $destination).Length
            if ($copiedHash -cne $expectedHash -or
                $copiedBytes -ne [uint64]($module.olean_bytes)) {
                throw "copied parent OLean changed bytes: $destination"
            }
            $expectedImportedHashes.Add($destination, $expectedHash)
        }
    }

    $afterImport = @(Get-Erdos848Oleans -Lean4Root $lean4)
    $observedImported = @($afterImport | ForEach-Object { $_.FullName } | Sort-Object)
    $declaredImported = @($expectedImported | Sort-Object)
    if ([string]::Join("`n", $observedImported) -cne
        [string]::Join("`n", $declaredImported)) {
        throw "project OLean inventory is not exactly the authenticated parent inventory"
    }

    foreach ($module in @($segment.modules)) {
        $name = [string]$module.name
        $sourceRelative = [string]$module.source_path
        $sourceFile = Join-Path $source $sourceRelative
        $oleanRelative = $name.Replace(".", "/") + ".olean"
        $destination = Join-Path (Join-Path $lean4 ".lake/build/lib/lean") $oleanRelative
        [void](New-Item -ItemType Directory -Path (Split-Path -Parent $destination) `
            -Force)
        $partial = Join-Path $env:RUNNER_TEMP `
            ("e848-segment-$SegmentIndex-" + $name.Replace(".", "-") + ".partial.olean")
        if (Test-Path -LiteralPath $partial) {
            throw "partial output unexpectedly exists: $partial"
        }
        $relativeToLean4 = [IO.Path]::GetRelativePath($lean4, $sourceFile)
        $leanArgs = @(
            "env", "lean", "--trust=0", "-q", "-M", [string]$MemoryMiB,
            "-D", "compiler.postponeCompile=true", "-o", $partial,
            $relativeToLean4
        )
        Invoke-Checked -Description "source compile $name" -Command {
            & $lake @leanArgs
        }
        if (-not (Test-Path -LiteralPath $partial -PathType Leaf)) {
            throw "Lean did not produce the expected OLean for $name"
        }
        Move-Item -LiteralPath $partial -Destination $destination
    }

    foreach ($entry in $expectedImportedHashes.GetEnumerator()) {
        $observedHash = (Get-FileHash -LiteralPath $entry.Key `
            -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($observedHash -cne $entry.Value) {
            throw "authenticated parent OLean changed during child compilation: $($entry.Key)"
        }
    }
}
finally {
    Pop-Location
}

$artifactOleans = Join-Path $output "oleans"
foreach ($module in @($segment.modules)) {
    $relative = ([string]$module.name).Replace(".", "/") + ".olean"
    $built = Join-Path (Join-Path $lean4 ".lake/build/lib/lean") $relative
    $published = Join-Path $artifactOleans $relative
    [void](New-Item -ItemType Directory -Path (Split-Path -Parent $published) -Force)
    Copy-Item -LiteralPath $built -Destination $published
}

$sealArgs = @(
    "-B", $planner, "seal-receipt",
    "--plan", $plan,
    "--source-root", $source,
    "--lock", $lock,
    "--segment-index", [string]$SegmentIndex,
    "--asset-root", $output,
    "--memory-mib", [string]$MemoryMiB,
    "--runner-os", $env:RUNNER_OS,
    "--runner-arch", $env:RUNNER_ARCH,
    "--lean-version", $leanVersion,
    "--output", (Join-Path $output "receipt.json")
)
foreach ($parent in $ParentRoot) {
    $sealArgs += @("--parent-root", ([IO.Path]::GetFullPath($parent)))
}
Invoke-Checked -Description "seal and verify canonical segment receipt" -Command {
    & $python @sealArgs
}

$verifyArgs = @(
    "-B", $planner, "verify-receipt",
    "--plan", $plan,
    "--asset-root", $output,
    "--segment-index", [string]$SegmentIndex
)
foreach ($parent in $ParentRoot) {
    $verifyArgs += @("--parent-root", ([IO.Path]::GetFullPath($parent)))
}
Invoke-Checked -Description "independently replay segment receipt verifier" -Command {
    & $python @verifyArgs
}
Write-Host "DIAGNOSTIC SOURCE CHECKPOINT SEGMENT PASSED index=$SegmentIndex"
