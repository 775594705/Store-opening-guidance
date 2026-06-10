$ErrorActionPreference = "Continue"

Write-Host "== Store Advisor Environment Check =="
Write-Host ""

$commands = @(
    @{Name = "node"; Args = "--version"},
    @{Name = "npm"; Args = "--version"},
    @{Name = "python"; Args = "--version"},
    @{Name = "pip"; Args = "--version"},
    @{Name = "git"; Args = "--version"},
    @{Name = "code"; Args = "--version"},
    @{Name = "cursor"; Args = "--version"}
)

foreach ($cmd in $commands) {
    Write-Host "[$($cmd.Name)]"
    try {
        & $cmd.Name $cmd.Args
    } catch {
        Write-Host "Not found or not configured in PATH"
    }
    Write-Host ""
}

Write-Host "[python launcher]"
try {
    py -0p
} catch {
    Write-Host "Python launcher not found"
}

