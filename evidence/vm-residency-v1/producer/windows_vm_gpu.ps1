param(
    [Parameter(Mandatory)][string]$StagePath,
    [Parameter(Mandatory)][string]$OutputPath,
    [Parameter(Mandatory)][string]$StopPath,
    [int]$MaximumSeconds = 2100
)
# Read-only Windows VidMm process counters. Sum every VM instance in analysis;
# aliases/shared allocations may overcount. Never subtract a desktop baseline.
$ErrorActionPreference = 'Stop'
$deadline = [DateTime]::UtcNow.AddSeconds($MaximumSeconds)
$utf8 = [Text.UTF8Encoding]::new($false)
while ([DateTime]::UtcNow -lt $deadline -and -not (Test-Path -LiteralPath $StopPath)) {
    $row = @{at=[DateTime]::UtcNow.ToString('o'); stage='initial'}
    try {
        if (Test-Path -LiteralPath $StagePath) {$row.stage = [IO.File]::ReadAllText($StagePath).Trim()}
        $processes = @(Get-Process -Name vmwp -ErrorAction SilentlyContinue)
        $identities = @($processes | ForEach-Object {@{pid=$_.Id; name=$_.ProcessName}})
        $ids = @($processes.Id)
        $rows = @(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory -OperationTimeoutSec 5 |
            Where-Object {$_.Name -match '^pid_(\d+)_' -and [int]$Matches[1] -in $ids} |
            ForEach-Object {
                $idMatch = [regex]::Match($_.Name, '^pid_(\d+)_')
                @{
                    instance=$_.Name; pid=[int]$idMatch.Groups[1].Value
                    dedicated_bytes=[uint64]$_.DedicatedUsage
                    shared_bytes=[uint64]$_.SharedUsage
                    committed_bytes=[uint64]$_.TotalCommitted
                }
            })
        if (-not $identities.Count -or -not $rows.Count) {throw 'No VM identities or GPU counters; no zero-usage inference is valid.'}
        $row.vm_processes = $identities
        $row.counters = $rows
        $row.collected_at = [DateTime]::UtcNow.ToString('o')
    } catch {
        $row.sampling_error = $_.Exception.Message
    }
    [IO.File]::AppendAllText($OutputPath, (($row | ConvertTo-Json -Depth 5 -Compress) + "`n"), $utf8)
    Start-Sleep -Milliseconds 1000
}
