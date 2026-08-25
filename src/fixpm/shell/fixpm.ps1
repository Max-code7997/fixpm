# fixpm PowerShell hook
# Enable with:  . (fixpm --init powershell)
# Add that line to your $PROFILE (e.g.
#   Documents\PowerShell\Microsoft.PowerShell_profile.ps1)

if (-not $global:__FixpmLoaded) {
    $global:__FixpmLoaded = $true

    function __Fixpm-Hook {
        if ($global:__FixpmBusy) { return }
        $h = Get-History -Count 1
        if (-not $h) { return }
        $cmd = [string]$h.CommandLine
        if ([string]::IsNullOrWhiteSpace($cmd)) { return }
        $ec = $LASTEXITCODE
        if ($null -eq $ec) { $ec = 0 }

        $global:__FixpmBusy = $true
        try {
            $env:FIXPM_LAST_COMMAND = $cmd
            $env:FIXPM_LAST_EXIT_CODE = "$ec"
            if ($env:FIXPM_DEBUG) {
                Write-Host "fixpm hook: cmd=$cmd ec=$ec" -ForegroundColor DarkYellow
            }
            if ($ec -eq 0) { return }
            if ($cmd -notmatch '^(npm|npx|pnpx|pnpm|yarn)(\s|$)') { return }
            if ($cmd -match '^(fixpm|npm -v)') { return }

            # Run the probe without clobbering $LASTEXITCODE for the user.
            $prev = $LASTEXITCODE
            $out = & fixpm --dry-run $cmd 2>$null
            $probeRc = $LASTEXITCODE
            $global:LASTEXITCODE = $prev
            if ($probeRc -eq 0 -and $out) {
                Write-Host "  fix available -- run fixpm" -ForegroundColor Yellow
            }
        } finally {
            $global:__FixpmBusy = $false
        }
    }

    # Wrap whatever prompt the user already has (oh-my-posh, starship, ...).
    if (-not $global:__FixpmWrapped) {
        $global:__FixpmOriginalPrompt = $function:prompt
        function global:prompt {
            & $global:__FixpmOriginalPrompt
            __Fixpm-Hook
        }
        $global:__FixpmWrapped = $true
    }
}
