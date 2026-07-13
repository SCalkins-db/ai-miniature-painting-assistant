# ==========================================================
# Project Tree with File Sizes
# ==========================================================

$OutputFile = "project_tree.txt"

$ExcludeDirs = @(
    ".git",
    ".venv",
    "__pycache__",
    ".idea",
    "node_modules"
)

function Format-Size {
    param([long]$Bytes)

    if ($Bytes -ge 1TB) {
        return "{0:N2} TB" -f ($Bytes / 1TB)
    }
    elseif ($Bytes -ge 1GB) {
        return "{0:N2} GB" -f ($Bytes / 1GB)
    }
    elseif ($Bytes -ge 1MB) {
        return "{0:N2} MB" -f ($Bytes / 1MB)
    }
    elseif ($Bytes -ge 1KB) {
        return "{0:N2} KB" -f ($Bytes / 1KB)
    }
    else {
        return "$Bytes B"
    }
}

function Show-Tree {
    param(
        [string]$Path = ".",
        [string]$Prefix = ""
    )

    $Items = @(
        Get-ChildItem -LiteralPath $Path -Force |
            Where-Object {
                $ExcludeDirs -notcontains $_.Name
            } |
            Sort-Object `
                @{ Expression = { $_.PSIsContainer }; Descending = $true },
                @{ Expression = { $_.Name }; Ascending = $true }
    )

    for ($i = 0; $i -lt $Items.Count; $i++) {
        $Item = $Items[$i]
        $Last = ($i -eq ($Items.Count - 1))

        if ($Last) {
            $Branch = "\---"
            $NextPrefix = "$Prefix    "
        }
        else {
            $Branch = "+---"
            $NextPrefix = "$Prefix|   "
        }

        if ($Item.PSIsContainer) {
            Add-Content -LiteralPath $OutputFile -Value "$Prefix$Branch[$($Item.Name)]"
            Show-Tree -Path $Item.FullName -Prefix $NextPrefix
        }
        else {
            $Size = Format-Size -Bytes $Item.Length
            $Modified = $Item.LastWriteTime.ToString("yyyy-MM-dd HH:mm")

            $Line = "$Prefix$Branch{0,-45} {1,10}   {2}" -f `
                $Item.Name,
                $Size,
                $Modified

            Add-Content -LiteralPath $OutputFile -Value $Line
        }
    }
}

Set-Content -LiteralPath $OutputFile -Value @(
    "============================================================"
    "PROJECT TREE"
    "Generated: $(Get-Date)"
    "Root: $(Get-Location)"
    "============================================================"
    ""
)

Show-Tree

Write-Host ""
Write-Host "Done."
Write-Host "Output written to $OutputFile"