param([string]$OutputPath = 'evidence/host-vram.json')
$ErrorActionPreference = 'Stop'
$usage = @(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory | Sort-Object DedicatedUsage -Descending | Select-Object -First 20)
$rows = foreach ($entry in $usage) {
    if ($entry.Name -match '^pid_(\d+)_') {
        $processId = [int]$Matches[1]
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        [ordered]@{pid=$processId; process=$process.ProcessName; dedicated_mib=[Math]::Round($entry.DedicatedUsage/1MB,1)}
    }
}
$report = [ordered]@{
    captured_at=[DateTime]::UtcNow.ToString('o')
    gpu=@(nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader)
    processes=@($rows)
    notes=@('WDDM process counters may overlap; do not sum as physical GPU usage.', 'DWM is the desktop compositor: avoid terminating it.', 'Close unused browser tabs or disable browser acceleration after saving work.', 'Use a lower resolution or fewer active displays to reduce compositor surfaces.', 'Inference can offload weights or KV cache to RAM, at a measurable throughput cost.')
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding utf8
$report | ConvertTo-Json -Depth 6
