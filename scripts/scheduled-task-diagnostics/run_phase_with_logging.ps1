param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("PRECLOSE", "CANONICAL_CLOSE")]
    [string]$Phase,

    [Parameter(Mandatory = $true)]
    [string]$PythonPath,

    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
$logRoot = Join-Path $ProjectRoot "backend\logs\scheduled-task-diagnostics"
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $logRoot "$Phase-$stamp.log"
$outFile = Join-Path $logRoot "$Phase-$stamp.stdout.txt"
$errFile = Join-Path $logRoot "$Phase-$stamp.stderr.txt"

$started = Get-Date
$header = @(
    "PHASE=$Phase"
    "STARTED_AT=$($started.ToString('o'))"
    "PROJECT_ROOT=$ProjectRoot"
    "PYTHON=$PythonPath"
    "COMMAND=-m backend.app.operations.scheduled_operation_phase_runner --phase $Phase"
    "USER=$([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)"
    "MACHINE=$env:COMPUTERNAME"
)
[System.IO.File]::WriteAllLines($logFile, $header, [System.Text.UTF8Encoding]::new($false))

$exitCode = 9009
try {
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    $proc = Start-Process `
        -FilePath $PythonPath `
        -ArgumentList @("-m", "backend.app.operations.scheduled_operation_phase_runner", "--phase", $Phase) `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $outFile `
        -RedirectStandardError $errFile `
        -Wait `
        -PassThru

    $exitCode = [int]$proc.ExitCode
}
catch {
    $message = "WRAPPER_EXCEPTION=$($_.Exception.ToString())"
    [System.IO.File]::AppendAllText($logFile, "`r`n$message`r`n", [System.Text.UTF8Encoding]::new($false))
    $_ | Out-String | Set-Content -LiteralPath $errFile -Encoding UTF8
    $exitCode = 9009
}
finally {
    $finished = Get-Date
    $tail = @(
        "FINISHED_AT=$($finished.ToString('o'))"
        "DURATION_SECONDS=$([Math]::Round(($finished - $started).TotalSeconds, 2))"
        "EXIT_CODE=$exitCode"
        "STDOUT_FILE=$outFile"
        "STDERR_FILE=$errFile"
    )
    [System.IO.File]::AppendAllText($logFile, (($tail -join "`r`n") + "`r`n"), [System.Text.UTF8Encoding]::new($false))
}

exit $exitCode

