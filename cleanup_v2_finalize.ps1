<#
.SYNOPSIS
    Final Cleanup V2 script for AI Miniature Painting Assistant.

.DESCRIPTION
    Default behavior is DRY RUN.

    This script can:
      - Move acquisition logs into legacy reports.
      - Move database backups to backups/database.
      - Move project tree reports into reports/project_audit.
      - Consolidate duplicate enrichment_analysis.md.
      - Detect duplicate source documents and extracted text by SHA-256.
      - Preserve one canonical copy and move redundant copies into legacy/duplicates.
      - Optionally compress legacy workflow CSV archives.
      - Remove Python cache files.
      - Remove empty directories.
      - Run Python compile validation.
      - Write a move manifest and cleanup log.

    Nothing changes unless -Apply is supplied.

.EXAMPLES
    Preview only:
        powershell -ExecutionPolicy Bypass -File .\cleanup_v2_finalize.ps1

    Apply cleanup:
        powershell -ExecutionPolicy Bypass -File .\cleanup_v2_finalize.ps1 -Apply

    Apply cleanup and compress the old workflow CSV archive:
        powershell -ExecutionPolicy Bypass -File .\cleanup_v2_finalize.ps1 -Apply -CompressLegacyCsv

    Apply, compress, and remove the original imported CSV folder after verifying ZIP:
        powershell -ExecutionPolicy Bypass -File .\cleanup_v2_finalize.ps1 -Apply -CompressLegacyCsv -RemoveCompressedSource

    Run even with uncommitted Git changes:
        powershell -ExecutionPolicy Bypass -File .\cleanup_v2_finalize.ps1 -Apply -AllowDirty
#>

[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$AllowDirty,
    [switch]$CompressLegacyCsv,
    [switch]$RemoveCompressedSource,
    [switch]$RunApplication
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Get-Location).Path
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$LogRoot = Join-Path $ProjectRoot "reports\project_audit"
$LogFile = Join-Path $LogRoot "cleanup_v2_$Timestamp.log"
$ManifestFile = Join-Path $LogRoot "cleanup_v2_manifest_$Timestamp.csv"

$ExcludedRoots = @(
    ".git",
    ".venv",
    ".idea",
    "node_modules",
    "__pycache__"
)

$Manifest = New-Object System.Collections.Generic.List[object]

function Write-Log {
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [ValidateSet("INFO", "WARN", "ERROR", "MOVE", "CREATE", "DELETE", "CHECK", "HASH", "ZIP")]
        [string]$Level = "INFO"
    )

    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Write-Host $line

    if ($Apply) {
        if (-not (Test-Path -LiteralPath $LogRoot)) {
            New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null
        }

        Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    }
}

function Add-ManifestEntry {
    param(
        [string]$Action,
        [string]$Source,
        [string]$Destination,
        [string]$Reason,
        [string]$Hash = ""
    )

    $Manifest.Add([pscustomobject]@{
        Timestamp   = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        Action      = $Action
        Source      = $Source
        Destination = $Destination
        Reason      = $Reason
        SHA256      = $Hash
    }) | Out-Null
}

function Save-Manifest {
    if (-not $Apply) {
        return
    }

    if (-not (Test-Path -LiteralPath $LogRoot)) {
        New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null
    }

    $Manifest | Export-Csv -LiteralPath $ManifestFile -NoTypeInformation -Encoding UTF8
}

function Get-RelativePath {
    param([Parameter(Mandatory)][string]$FullPath)

    return [System.IO.Path]::GetRelativePath($ProjectRoot, $FullPath)
}

function Ensure-Directory {
    param([Parameter(Mandatory)][string]$RelativePath)

    $fullPath = Join-Path $ProjectRoot $RelativePath

    if (Test-Path -LiteralPath $fullPath) {
        return
    }

    if ($Apply) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Log "Created directory: $RelativePath" "CREATE"
        Add-ManifestEntry -Action "CREATE_DIR" -Source "" -Destination $RelativePath -Reason "Cleanup destination"
    }
    else {
        Write-Log "DRY RUN: create directory $RelativePath" "CREATE"
    }
}

function Move-ItemSafe {
    param(
        [Parameter(Mandatory)][string]$SourceRelative,
        [Parameter(Mandatory)][string]$DestinationRelative,
        [Parameter(Mandatory)][string]$Reason,
        [string]$Hash = ""
    )

    $source = Join-Path $ProjectRoot $SourceRelative
    $destination = Join-Path $ProjectRoot $DestinationRelative

    if (-not (Test-Path -LiteralPath $source)) {
        Write-Log "Source not found; skipping: $SourceRelative" "WARN"
        return
    }

    $destinationParent = Split-Path -Parent $destination
    if (-not (Test-Path -LiteralPath $destinationParent)) {
        $parentRelative = Get-RelativePath $destinationParent
        Ensure-Directory $parentRelative
    }

    if (Test-Path -LiteralPath $destination) {
        throw "Destination already exists: $DestinationRelative"
    }

    if ($Apply) {
        Move-Item -LiteralPath $source -Destination $destination
        Write-Log "$SourceRelative -> $DestinationRelative" "MOVE"
        Add-ManifestEntry -Action "MOVE" -Source $SourceRelative -Destination $DestinationRelative -Reason $Reason -Hash $Hash
    }
    else {
        Write-Log "DRY RUN: move $SourceRelative -> $DestinationRelative ($Reason)" "MOVE"
    }
}

function Remove-ItemSafe {
    param(
        [Parameter(Mandatory)][string]$RelativePath,
        [Parameter(Mandatory)][string]$Reason
    )

    $fullPath = Join-Path $ProjectRoot $RelativePath

    if (-not (Test-Path -LiteralPath $fullPath)) {
        return
    }

    if ($Apply) {
        Remove-Item -LiteralPath $fullPath -Recurse -Force
        Write-Log "Removed: $RelativePath" "DELETE"
        Add-ManifestEntry -Action "DELETE" -Source $RelativePath -Destination "" -Reason $Reason
    }
    else {
        Write-Log "DRY RUN: remove $RelativePath ($Reason)" "DELETE"
    }
}

function Test-ProjectRoot {
    $required = @(
        "main.py",
        "src",
        "data",
        "database",
        "tools"
    )

    foreach ($item in $required) {
        if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot $item))) {
            throw "This does not appear to be the project root. Missing: $item"
        }
    }

    Write-Log "Project root confirmed: $ProjectRoot" "CHECK"
}

function Test-GitState {
    $git = Get-Command git -ErrorAction SilentlyContinue

    if (-not $git) {
        Write-Log "Git not found. Continuing without Git safety checks." "WARN"
        return
    }

    & git rev-parse --is-inside-work-tree *> $null

    if ($LASTEXITCODE -ne 0) {
        Write-Log "Not inside a Git repository. Continuing." "WARN"
        return
    }

    $status = & git status --porcelain

    if ($status -and -not $AllowDirty) {
        throw @"
Git has uncommitted changes.

Commit or stash them first, or rerun with -AllowDirty.

Current changes:
$($status -join [Environment]::NewLine)
"@
    }

    if ($status) {
        Write-Log "Git working tree is dirty; continuing because -AllowDirty was supplied." "WARN"
    }
    else {
        Write-Log "Git working tree is clean." "CHECK"
    }
}

function Get-Sha256 {
    param([Parameter(Mandatory)][string]$Path)

    Write-Log "Hashing: $(Get-RelativePath $Path)" "HASH"
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-PreferredCanonicalPath {
    param(
        [Parameter(Mandatory)]
        [System.Collections.Generic.List[System.IO.FileInfo]]$Files
    )

    $ordered = $Files | Sort-Object `
        @{ Expression = {
            $relative = (Get-RelativePath $_.FullName).Replace("\", "/").ToLowerInvariant()

            if ($relative -like "data/source_documents/army_painter/*") { return 0 }
            if ($relative -like "data/source_documents/vallejo/*") { return 1 }
            if ($relative -like "data/source_documents/ak_interactive/*") { return 2 }
            if ($relative -like "data/imports/extracted_text/army_painter/*") { return 3 }
            if ($relative -like "data/imports/extracted_text/vallejo/*") { return 4 }
            if ($relative -like "data/imports/extracted_text/ak_interactive/*") { return 5 }

            return 50
        }; Ascending = $true },
        @{ Expression = { $_.FullName.Length }; Ascending = $true },
        @{ Expression = { $_.FullName }; Ascending = $true }

    return $ordered[0]
}

function Move-DuplicateGroup {
    param(
        [Parameter(Mandatory)][string]$Hash,
        [Parameter(Mandatory)]
        [System.Collections.Generic.List[System.IO.FileInfo]]$Files,
        [Parameter(Mandatory)][string]$Category
    )

    if ($Files.Count -lt 2) {
        return
    }

    $canonical = Get-PreferredCanonicalPath -Files $Files
    $canonicalRelative = Get-RelativePath $canonical.FullName

    Write-Log "Canonical $Category file: $canonicalRelative" "CHECK"

    foreach ($file in $Files) {
        if ($file.FullName -eq $canonical.FullName) {
            continue
        }

        $relative = Get-RelativePath $file.FullName
        $destination = Join-Path "legacy\duplicates" $relative

        Move-ItemSafe `
            -SourceRelative $relative `
            -DestinationRelative $destination `
            -Reason "Duplicate $Category; canonical copy retained at $canonicalRelative" `
            -Hash $Hash
    }
}

function Consolidate-DuplicateFiles {
    param(
        [Parameter(Mandatory)][string]$RelativeRoot,
        [Parameter(Mandatory)][string[]]$Extensions,
        [Parameter(Mandatory)][string]$Category
    )

    $fullRoot = Join-Path $ProjectRoot $RelativeRoot

    if (-not (Test-Path -LiteralPath $fullRoot)) {
        Write-Log "Duplicate scan root missing: $RelativeRoot" "WARN"
        return
    }

    $files = Get-ChildItem -LiteralPath $fullRoot -File -Recurse -Force |
        Where-Object {
            $Extensions -contains $_.Extension.ToLowerInvariant()
        }

    $sizeGroups = $files |
        Group-Object Length |
        Where-Object { $_.Count -gt 1 }

    $hashGroups = @{}

    foreach ($sizeGroup in $sizeGroups) {
        foreach ($file in $sizeGroup.Group) {
            $hash = Get-Sha256 -Path $file.FullName

            if (-not $hashGroups.ContainsKey($hash)) {
                $hashGroups[$hash] = New-Object System.Collections.Generic.List[System.IO.FileInfo]
            }

            $hashGroups[$hash].Add($file)
        }
    }

    foreach ($hash in $hashGroups.Keys) {
        $group = $hashGroups[$hash]

        if ($group.Count -gt 1) {
            Move-DuplicateGroup -Hash $hash -Files $group -Category $Category
        }
    }
}

function Move-AcquisitionLogs {
    $moves = @{
        "data\imports\image_processing_log.csv" = "legacy\reports\acquisition\image_processing_log.csv"
        "data\imports\video_processing_log.csv" = "legacy\reports\acquisition\video_processing_log.csv"
    }

    foreach ($source in $moves.Keys) {
        Move-ItemSafe `
            -SourceRelative $source `
            -DestinationRelative $moves[$source] `
            -Reason "Acquisition-era runtime log"
    }
}

function Move-DatabaseBackups {
    $sourceRoot = Join-Path $ProjectRoot "database\backups"

    if (-not (Test-Path -LiteralPath $sourceRoot)) {
        Write-Log "No database/backups directory found." "INFO"
        return
    }

    Ensure-Directory "backups\database"

    $files = Get-ChildItem -LiteralPath $sourceRoot -File -Force

    foreach ($file in $files) {
        $sourceRelative = Get-RelativePath $file.FullName
        $destinationRelative = Join-Path "backups\database" $file.Name

        Move-ItemSafe `
            -SourceRelative $sourceRelative `
            -DestinationRelative $destinationRelative `
            -Reason "Database backup separated from runtime database files"
    }
}

function Move-ProjectTreeReports {
    Ensure-Directory "reports\project_audit"

    $treeFiles = Get-ChildItem -LiteralPath $ProjectRoot -File -Force |
        Where-Object {
            $_.Name -like "project_tree*.txt"
        }

    foreach ($file in $treeFiles) {
        $sourceRelative = $file.Name
        $destinationRelative = Join-Path "reports\project_audit" $file.Name

        Move-ItemSafe `
            -SourceRelative $sourceRelative `
            -DestinationRelative $destinationRelative `
            -Reason "Generated project tree report"
    }
}

function Consolidate-EnrichmentAnalysis {
    $canonical = "docs\enrichment_analysis.md"
    $duplicate = "data\reports\enrichment_analysis.md"

    $canonicalFull = Join-Path $ProjectRoot $canonical
    $duplicateFull = Join-Path $ProjectRoot $duplicate

    if (-not (Test-Path -LiteralPath $canonicalFull) -or
        -not (Test-Path -LiteralPath $duplicateFull)) {
        Write-Log "Duplicate enrichment analysis pair not both present; skipping." "INFO"
        return
    }

    $canonicalHash = Get-Sha256 -Path $canonicalFull
    $duplicateHash = Get-Sha256 -Path $duplicateFull

    if ($canonicalHash -ne $duplicateHash) {
        Write-Log "enrichment_analysis.md files differ; leaving both for review." "WARN"
        return
    }

    Move-ItemSafe `
        -SourceRelative $duplicate `
        -DestinationRelative "legacy\duplicates\data\reports\enrichment_analysis.md" `
        -Reason "Exact duplicate of docs/enrichment_analysis.md" `
        -Hash $duplicateHash
}

function Consolidate-ReportBackups {
    $pairs = @(
        @{
            Primary = "data\reports\paint_equivalency_database.csv"
            Backup  = "data\reports\paint_equivalency_database_backup.csv"
        }
    )

    foreach ($pair in $pairs) {
        $primaryFull = Join-Path $ProjectRoot $pair.Primary
        $backupFull = Join-Path $ProjectRoot $pair.Backup

        if (-not (Test-Path -LiteralPath $primaryFull) -or
            -not (Test-Path -LiteralPath $backupFull)) {
            continue
        }

        $primaryHash = Get-Sha256 -Path $primaryFull
        $backupHash = Get-Sha256 -Path $backupFull

        if ($primaryHash -eq $backupHash) {
            Move-ItemSafe `
                -SourceRelative $pair.Backup `
                -DestinationRelative (Join-Path "legacy\duplicates" $pair.Backup) `
                -Reason "Exact duplicate backup report" `
                -Hash $backupHash
        }
        else {
            Write-Log "$($pair.Backup) differs from primary; leaving in place." "WARN"
        }
    }
}

function Move-ObviousNestedDataDuplicate {
    $source = "data\data\reports\missing_color_data_report.json"
    $destination = "legacy\duplicates\data\data\reports\missing_color_data_report.json"

    $sourceFull = Join-Path $ProjectRoot $source
    $canonicalFull = Join-Path $ProjectRoot "data\reports\missing_color_data_report.json"

    if (-not (Test-Path -LiteralPath $sourceFull)) {
        return
    }

    if (Test-Path -LiteralPath $canonicalFull) {
        $sourceHash = Get-Sha256 -Path $sourceFull
        $canonicalHash = Get-Sha256 -Path $canonicalFull

        if ($sourceHash -eq $canonicalHash) {
            Move-ItemSafe `
                -SourceRelative $source `
                -DestinationRelative $destination `
                -Reason "Duplicate nested data/data report" `
                -Hash $sourceHash
        }
        else {
            Write-Log "Nested missing_color_data_report.json differs from canonical file; leaving for review." "WARN"
        }
    }
}

function Compress-LegacyWorkflowCsv {
    if (-not $CompressLegacyCsv) {
        Write-Log "Legacy CSV compression not requested." "INFO"
        return
    }

    $sourceRelative = "legacy\archive\workflow_archive\imported"
    $sourceFull = Join-Path $ProjectRoot $sourceRelative

    if (-not (Test-Path -LiteralPath $sourceFull)) {
        Write-Log "Legacy imported workflow folder not found." "WARN"
        return
    }

    $archiveRootRelative = "legacy\archive\compressed"
    Ensure-Directory $archiveRootRelative

    $zipRelative = Join-Path $archiveRootRelative "workflow_archive_imported_$Timestamp.zip"
    $zipFull = Join-Path $ProjectRoot $zipRelative

    if ($Apply) {
        Write-Log "Compressing $sourceRelative -> $zipRelative" "ZIP"
        Compress-Archive -Path (Join-Path $sourceFull "*") -DestinationPath $zipFull -CompressionLevel Optimal -Force

        if (-not (Test-Path -LiteralPath $zipFull)) {
            throw "ZIP archive was not created: $zipRelative"
        }

        $zipInfo = Get-Item -LiteralPath $zipFull

        if ($zipInfo.Length -le 0) {
            throw "ZIP archive is empty: $zipRelative"
        }

        Write-Log "Created archive: $zipRelative ($([math]::Round($zipInfo.Length / 1MB, 2)) MB)" "ZIP"
        Add-ManifestEntry -Action "ZIP" -Source $sourceRelative -Destination $zipRelative -Reason "Compressed legacy workflow CSV archive"

        if ($RemoveCompressedSource) {
            $csvCount = @(Get-ChildItem -LiteralPath $sourceFull -File -Recurse -Filter "*.csv").Count

            if ($csvCount -eq 0) {
                Write-Log "No CSV files found under $sourceRelative; source not removed." "WARN"
            }
            else {
                Remove-ItemSafe `
                    -RelativePath $sourceRelative `
                    -Reason "Compressed to $zipRelative; $csvCount CSV files archived"
            }
        }
    }
    else {
        Write-Log "DRY RUN: compress $sourceRelative -> $zipRelative" "ZIP"

        if ($RemoveCompressedSource) {
            Write-Log "DRY RUN: remove source after successful ZIP verification." "DELETE"
        }
    }
}

function Remove-PythonCaches {
    $cacheDirs = Get-ChildItem -LiteralPath $ProjectRoot -Directory -Recurse -Force |
        Where-Object {
            $_.Name -eq "__pycache__" -and
            $_.FullName -notlike "*\.venv\*" -and
            $_.FullName -notlike "*\.git\*"
        } |
        Sort-Object { $_.FullName.Length } -Descending

    foreach ($dir in $cacheDirs) {
        Remove-ItemSafe `
            -RelativePath (Get-RelativePath $dir.FullName) `
            -Reason "Generated Python cache"
    }

    $compiledFiles = Get-ChildItem -LiteralPath $ProjectRoot -File -Recurse -Force |
        Where-Object {
            $_.Extension -in @(".pyc", ".pyo") -and
            $_.FullName -notlike "*\.venv\*" -and
            $_.FullName -notlike "*\.git\*"
        }

    foreach ($file in $compiledFiles) {
        Remove-ItemSafe `
            -RelativePath (Get-RelativePath $file.FullName) `
            -Reason "Generated compiled Python file"
    }
}

function Remove-EmptyDirectories {
    if (-not $Apply) {
        Write-Log "DRY RUN: remove empty directories, deepest first." "DELETE"
        return
    }

    do {
        $emptyDirs = Get-ChildItem -LiteralPath $ProjectRoot -Directory -Recurse -Force |
            Where-Object {
                $_.FullName -notlike "*\.git*" -and
                $_.FullName -notlike "*\.venv*" -and
                $_.FullName -notlike "*\.idea*" -and
                @(Get-ChildItem -LiteralPath $_.FullName -Force).Count -eq 0
            } |
            Sort-Object { $_.FullName.Length } -Descending

        foreach ($dir in $emptyDirs) {
            $relative = Get-RelativePath $dir.FullName
            Remove-Item -LiteralPath $dir.FullName -Force
            Write-Log "Removed empty directory: $relative" "DELETE"
            Add-ManifestEntry -Action "DELETE_DIR" -Source $relative -Destination "" -Reason "Empty directory"
        }
    }
    while ($emptyDirs.Count -gt 0)
}

function Invoke-PythonValidation {
    $python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

    if (-not (Test-Path -LiteralPath $python)) {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue

        if (-not $pythonCommand) {
            Write-Log "Python not found; validation skipped." "WARN"
            return
        }

        $python = $pythonCommand.Source
    }

    Write-Log "Running compile validation." "CHECK"
    & $python -m compileall -q (Join-Path $ProjectRoot "src") (Join-Path $ProjectRoot "main.py")

    if ($LASTEXITCODE -ne 0) {
        throw "Python compile validation failed."
    }

    Write-Log "Python compile validation passed." "CHECK"

    if ($RunApplication) {
        Write-Log "Launching main.py." "CHECK"
        & $python (Join-Path $ProjectRoot "main.py")

        if ($LASTEXITCODE -ne 0) {
            throw "main.py exited with code $LASTEXITCODE."
        }
    }
}

function Show-Summary {
    Write-Host ""
    Write-Host "============================================================"

    if ($Apply) {
        Write-Host "Cleanup V2 completed."
        Write-Host "Log:      $LogFile"
        Write-Host "Manifest: $ManifestFile"
    }
    else {
        Write-Host "Dry run completed. No files were changed."
        Write-Host ""
        Write-Host "Apply with:"
        Write-Host "powershell -ExecutionPolicy Bypass -File .\cleanup_v2_finalize.ps1 -Apply"
    }

    Write-Host "============================================================"
}

try {
    Test-ProjectRoot
    Test-GitState

    Write-Log "Mode: $(if ($Apply) { 'APPLY' } else { 'DRY RUN' })" "INFO"

    Ensure-Directory "legacy\duplicates"
    Ensure-Directory "legacy\reports\acquisition"
    Ensure-Directory "backups\database"
    Ensure-Directory "reports\project_audit"

    Move-AcquisitionLogs
    Move-DatabaseBackups
    Move-ProjectTreeReports
    Consolidate-EnrichmentAnalysis
    Consolidate-ReportBackups
    Move-ObviousNestedDataDuplicate

    Consolidate-DuplicateFiles `
        -RelativeRoot "data\source_documents" `
        -Extensions @(".pdf", ".xlsx", ".docx", ".jpg", ".jpeg", ".png", ".webp") `
        -Category "source document"

    Consolidate-DuplicateFiles `
        -RelativeRoot "data\imports\extracted_text" `
        -Extensions @(".txt") `
        -Category "extracted text"

    Compress-LegacyWorkflowCsv
    Remove-PythonCaches
    Remove-EmptyDirectories

    if ($Apply) {
        Save-Manifest
        Invoke-PythonValidation
    }
    else {
        Write-Log "DRY RUN: compile validation will run after applying changes." "CHECK"
    }

    Show-Summary
}
catch {
    Write-Log $_.Exception.Message "ERROR"

    if ($Apply) {
        Save-Manifest
    }

    Write-Host ""
    Write-Host "Cleanup stopped."
    Write-Host "Review:"
    Write-Host "  git status --short"
    Write-Host "  git diff"
    Write-Host ""
    Write-Host "No automatic rollback was attempted."
    exit 1
}
