param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 75)]
    [int]$StartPart,

    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 75)]
    [int]$EndPart,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

if ($StartPart -gt $EndPart) {
    throw "StartPart must be at most EndPart"
}

$ManifestSha256 = "3cbde25db4c5eac8209dd428cc5d95eab648766023db87418c8ea8c66353c527"
$ManifestUrl = "https://github.com/crabsatellite/erdos-848-squarefree-product/releases/download/v1.0.5-kernel/ERDOS848_OLEAN_CACHE_MANIFEST.json"
$ReleaseBaseUrl = "https://github.com/crabsatellite/erdos-848-squarefree-product/releases/download/v1.0.5-kernel"
Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class E848NativeDisk
{
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern uint GetCompressedFileSizeW(
        string lpFileName,
        out uint lpFileSizeHigh
    );
}
"@

function Get-CompressedAllocationBytes {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)

    [uint32]$high = 0
    [uint32]$low = [E848NativeDisk]::GetCompressedFileSizeW(
        $LiteralPath,
        [ref]$high
    )
    if ($low -eq [uint32]::MaxValue) {
        $errorCode = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        if ($errorCode -ne 0) {
            throw "GetCompressedFileSizeW failed for $LiteralPath (Win32 $errorCode)"
        }
    }
    return [uint64]$high * [uint64]4294967296 + [uint64]$low
}

function Get-FixedDiskSnapshot {
    return @(
        Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" |
            Sort-Object DeviceID |
            ForEach-Object {
                [ordered]@{
                    device_id = [string]$_.DeviceID
                    filesystem = [string]$_.FileSystem
                    size_bytes = [uint64]$_.Size
                    free_bytes = [uint64]$_.FreeSpace
                }
            }
    )
}

function Get-PageFileSnapshot {
    return @(
        Get-CimInstance Win32_PageFileUsage |
            Sort-Object Name |
            ForEach-Object {
                [ordered]@{
                    name = [string]$_.Name
                    allocated_base_bytes = [uint64]$_.AllocatedBaseSize * [uint64]1MB
                    current_usage_bytes = [uint64]$_.CurrentUsage * [uint64]1MB
                    peak_usage_bytes = [uint64]$_.PeakUsage * [uint64]1MB
                    temporary = [bool]$_.TempPageFile
                }
            }
    )
}

function Get-Snapshot {
    param([Parameter(Mandatory = $true)][string]$Phase)

    return [ordered]@{
        phase = $Phase
        utc = [DateTime]::UtcNow.ToString("o")
        fixed_disks = @(Get-FixedDiskSnapshot)
        pagefiles = @(Get-PageFileSnapshot)
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

$scratchBase = [IO.Path]::GetFullPath((Join-Path $env:RUNNER_TEMP "e848-ntfs-measure"))
$outputFull = [IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $scratchBase) {
    throw "scratch path unexpectedly exists: $scratchBase"
}
[void](New-Item -ItemType Directory -Path $scratchBase)

$scratchDrive = [IO.Path]::GetPathRoot($scratchBase).TrimEnd("\")
$volume = Get-CimInstance Win32_Volume -Filter "DriveLetter='$scratchDrive'"
if ($null -eq $volume) {
    throw "cannot resolve scratch volume $scratchDrive"
}
if ([string]$volume.FileSystem -cne "NTFS") {
    throw "scratch volume is not NTFS: $($volume.FileSystem)"
}
if ([uint64]$volume.BlockSize -eq 0) {
    throw "scratch volume reports a zero cluster size"
}

$manifestPath = Join-Path $scratchBase "ERDOS848_OLEAN_CACHE_MANIFEST.json"
Invoke-CurlDownload -Url $ManifestUrl -Destination $manifestPath
$observedManifestSha = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($observedManifestSha -cne $ManifestSha256) {
    throw "manifest SHA-256 mismatch: $observedManifestSha"
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json

if ([int]$manifest.summary.archives -ne 75) {
    throw "manifest archive count is not 75"
}
if ([int]$manifest.summary.modules -ne 30638) {
    throw "manifest module count is not 30638"
}
if ([uint64]$manifest.summary.raw_bytes -ne [uint64]129476102424) {
    throw "manifest raw-byte total is unexpected"
}

$computer = Get-CimInstance Win32_ComputerSystem
$operatingSystem = Get-CimInstance Win32_OperatingSystem
$processor = @(Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name)
$initialSnapshot = Get-Snapshot -Phase "initial"
$parts = [System.Collections.Generic.List[object]]::new()

for ($part = $StartPart; $part -le $EndPart; $part++) {
    $partLabel = $part.ToString("000")
    $archive = @($manifest.archives | Where-Object {
        [string]$_.archive -match "part-$partLabel-of-075[.]zip$"
    })
    if ($archive.Count -ne 1) {
        throw "expected one manifest archive for part $partLabel, found $($archive.Count)"
    }
    $archive = $archive[0]
    $expectedFiles = @($manifest.files | Where-Object {
        [string]$_.archive -ceq [string]$archive.archive
    })
    if ($expectedFiles.Count -eq 0) {
        throw "manifest has no files for $($archive.archive)"
    }

    $partRoot = [IO.Path]::GetFullPath((Join-Path $scratchBase "part-$partLabel"))
    if (-not $partRoot.StartsWith($scratchBase + [IO.Path]::DirectorySeparatorChar, [StringComparison]::Ordinal)) {
        throw "part path escaped scratch root: $partRoot"
    }
    [void](New-Item -ItemType Directory -Path $partRoot)
    $zipPath = Join-Path $partRoot ([string]$archive.archive)
    $extractRoot = Join-Path $partRoot "extracted"
    [void](New-Item -ItemType Directory -Path $extractRoot)

    Write-Host "PART $partLabel download $($archive.archive)"
    $snapshots = [System.Collections.Generic.List[object]]::new()
    $snapshots.Add((Get-Snapshot -Phase "before-download"))
    Invoke-CurlDownload `
        -Url "$ReleaseBaseUrl/$($archive.archive)" `
        -Destination $zipPath
    $snapshots.Add((Get-Snapshot -Phase "after-download"))

    $zipInfo = Get-Item -LiteralPath $zipPath
    if ([uint64]$zipInfo.Length -ne [uint64]$archive.archive_bytes) {
        throw "archive byte count mismatch for $($archive.archive)"
    }
    $zipSha = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($zipSha -cne [string]$archive.archive_sha256) {
        throw "archive SHA-256 mismatch for $($archive.archive): $zipSha"
    }

    & tar.exe -xf $zipPath -C $extractRoot
    if ($LASTEXITCODE -ne 0) {
        throw "tar extraction failed for $($archive.archive) with exit code $LASTEXITCODE"
    }
    $snapshots.Add((Get-Snapshot -Phase "after-extract"))

    $actualFiles = @(Get-ChildItem -LiteralPath $extractRoot -Recurse -File)
    if ($actualFiles.Count -ne $expectedFiles.Count) {
        throw "file-count mismatch for $($archive.archive): actual=$($actualFiles.Count) expected=$($expectedFiles.Count)"
    }
    if (@($actualFiles | Where-Object { $_.Extension -cne ".olean" }).Count -ne 0) {
        throw "archive contains a non-.olean file: $($archive.archive)"
    }

    $expectedMap = [Collections.Generic.Dictionary[string, object]]::new(
        [StringComparer]::Ordinal
    )
    foreach ($entry in $expectedFiles) {
        $path = [string]$entry.cache_path
        if ($expectedMap.ContainsKey($path)) {
            throw "duplicate manifest cache path: $path"
        }
        $expectedMap.Add($path, $entry)
    }

    [uint64]$logicalBytes = 0
    foreach ($file in $actualFiles) {
        $relative = [IO.Path]::GetRelativePath($extractRoot, $file.FullName).Replace("\", "/")
        if (-not $expectedMap.ContainsKey($relative)) {
            throw "unexpected extracted path in $($archive.archive): $relative"
        }
        $entry = $expectedMap[$relative]
        if ([uint64]$file.Length -ne [uint64]$entry.cache_bytes) {
            throw "logical-size mismatch for $relative"
        }
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($hash -cne [string]$entry.cache_sha256) {
            throw "cache SHA-256 mismatch for $relative: $hash"
        }
        $logicalBytes += [uint64]$file.Length
        [void]$expectedMap.Remove($relative)
    }
    if ($expectedMap.Count -ne 0) {
        throw "missing $($expectedMap.Count) manifest paths in $($archive.archive)"
    }
    if ($logicalBytes -ne [uint64]$archive.raw_bytes) {
        throw "raw-byte mismatch for $($archive.archive): $logicalBytes"
    }

    Write-Host "PART $partLabel compact exact .olean files"
    Push-Location $extractRoot
    try {
        & compact.exe /C /S /I /F /Q /A "*.olean" | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "compact.exe failed for $($archive.archive) with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }

    [uint64]$allocatedBytes = 0
    $compressedCount = 0
    foreach ($file in $actualFiles) {
        $refreshed = Get-Item -LiteralPath $file.FullName -Force
        if (($refreshed.Attributes -band [IO.FileAttributes]::Compressed) -eq 0) {
            throw "NTFS compressed attribute is absent after compact.exe: $($file.FullName)"
        }
        $compressedCount++
        $allocatedBytes += Get-CompressedAllocationBytes -LiteralPath $file.FullName
    }
    $snapshots.Add((Get-Snapshot -Phase "after-compact"))

    $partRecord = [ordered]@{
        part = $part
        archive = [string]$archive.archive
        archive_bytes = [uint64]$zipInfo.Length
        archive_sha256 = $zipSha
        file_count = $actualFiles.Count
        compressed_attribute_file_count = $compressedCount
        logical_bytes = $logicalBytes
        ntfs_allocated_bytes = $allocatedBytes
        ntfs_allocation_ratio = [double]$allocatedBytes / [double]$logicalBytes
        snapshots = @($snapshots)
    }
    $parts.Add($partRecord)
    Write-Host ("PART {0} exact_files={1} logical={2} ntfs_allocated={3} ratio={4:N6}" -f `
        $partLabel, $actualFiles.Count, $logicalBytes, $allocatedBytes, `
        ([double]$allocatedBytes / [double]$logicalBytes))

    Remove-Item -LiteralPath $partRoot -Recurse -Force
    Start-Sleep -Seconds 1
    $partRecord["cleanup_snapshot"] = Get-Snapshot -Phase "after-cleanup"
}

$finalSnapshot = Get-Snapshot -Phase "final"
[uint64]$totalArchiveBytes = 0
[uint64]$totalLogicalBytes = 0
[uint64]$totalAllocatedBytes = 0
$totalFiles = 0
foreach ($partRecord in $parts) {
    $totalArchiveBytes += [uint64]$partRecord.archive_bytes
    $totalLogicalBytes += [uint64]$partRecord.logical_bytes
    $totalAllocatedBytes += [uint64]$partRecord.ntfs_allocated_bytes
    $totalFiles += [int]$partRecord.file_count
}

$report = [ordered]@{
    schema_version = 1
    manifest_sha256 = $observedManifestSha
    release_tag = "v1.0.5-kernel"
    range = [ordered]@{ start_part = $StartPart; end_part = $EndPart }
    github = [ordered]@{
        repository = [string]$env:GITHUB_REPOSITORY
        run_id = [string]$env:GITHUB_RUN_ID
        run_attempt = [string]$env:GITHUB_RUN_ATTEMPT
        sha = [string]$env:GITHUB_SHA
    }
    runner = [ordered]@{
        name = [string]$env:RUNNER_NAME
        os = [string]$env:RUNNER_OS
        architecture = [string]$env:RUNNER_ARCH
        image_os = [string]$env:ImageOS
        image_version = [string]$env:ImageVersion
        physical_memory_bytes = [uint64]$computer.TotalPhysicalMemory
        logical_processors = [int]$computer.NumberOfLogicalProcessors
        processor_names = $processor
        operating_system = [string]$operatingSystem.Caption
        operating_system_version = [string]$operatingSystem.Version
        scratch_root = $scratchBase
        scratch_drive = $scratchDrive
        scratch_filesystem = [string]$volume.FileSystem
        scratch_cluster_bytes = [uint64]$volume.BlockSize
        scratch_capacity_bytes = [uint64]$volume.Capacity
    }
    initial_snapshot = $initialSnapshot
    parts = @($parts)
    totals = [ordered]@{
        parts = $parts.Count
        files = $totalFiles
        archive_bytes = $totalArchiveBytes
        logical_bytes = $totalLogicalBytes
        ntfs_allocated_bytes = $totalAllocatedBytes
        ntfs_allocation_ratio = [double]$totalAllocatedBytes / [double]$totalLogicalBytes
    }
    final_snapshot = $finalSnapshot
}

$outputParent = Split-Path -Parent $outputFull
if (-not (Test-Path -LiteralPath $outputParent)) {
    [void](New-Item -ItemType Directory -Path $outputParent)
}
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $outputFull -Encoding utf8NoBOM
Write-Host "REPORT $outputFull"
Write-Host ("TOTAL parts={0} files={1} logical={2} ntfs_allocated={3} ratio={4:N6}" -f `
    $parts.Count, $totalFiles, $totalLogicalBytes, $totalAllocatedBytes, `
    ([double]$totalAllocatedBytes / [double]$totalLogicalBytes))
