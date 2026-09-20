# fixpm PowerShell hook
#
# Enable by adding this line to your $PROFILE (e.g.
#   Documents\PowerShell\Microsoft.PowerShell_profile.ps1):
#
#   fixpm --init powershell > $env:TEMP\fixpm-hook.ps1; . "$env:TEMP\fixpm-hook.ps1"
#
# Do NOT use `. (fixpm --init powershell)`. PowerShell's dot-source operator
# treats the string it is handed as a *file path*, not as script text, so that
# form throws "is not recognized as the name of a cmdlet" at every shell
# startup and installs nothing.

if (-not $global:__FixpmLoaded) {
    $global:__FixpmLoaded = $true

    # Run the typo probe. Prefers the compiled fixpm-probe: this sits on the
    # prompt path, where the Python CLI's interpreter start-up is directly felt
    # as a pause after every failed npm command. The --deadline budget means a
    # slow npm registry can never hold the prompt hostage.
    # Resolved once at load time rather than on every prompt.
    $global:__FixpmProbe = if (Get-Command fixpm-probe -ErrorAction SilentlyContinue) {
        { param([string]$c) & fixpm-probe --deadline 400ms --dry-run $c }
    } else {
        { param([string]$c) & fixpm --dry-run $c }
    }

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
            $out = & $global:__FixpmProbe $cmd 2>$null
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
