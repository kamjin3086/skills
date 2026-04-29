param(
    [string]$BaseUrl = $env:LEMONADE_BASE_URL,
    [string]$ApiKey = $env:LEMONADE_API_KEY,
    [string]$OutFile = ".\omni_capabilities.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://127.0.0.1:13305"
}

$headers = @{}
if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
    $headers["Authorization"] = "Bearer $ApiKey"
}

function Invoke-EndpointProbe {
    param([string]$Path)
    try {
        Invoke-WebRequest -Uri ($BaseUrl + $Path) -Method Post -ContentType "application/json" -Body "{}" -Headers $headers -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $code = [int]$_.Exception.Response.StatusCode.value__
            if ($code -eq 404 -or $code -eq 405) {
                return $false
            }
            return $true
        }
        throw
    }
}

$models = Invoke-RestMethod -Uri ($BaseUrl + "/v1/models?show_all=true") -Method Get -Headers $headers
$hasErrorProp = $models.PSObject.Properties.Name -contains "error"
if ($hasErrorProp -and $null -ne $models.error) {
    throw ("/v1/models returned error: " + ($models | ConvertTo-Json -Depth 8))
}

$allLabels = @()
foreach ($m in ($models.data | Where-Object { $_ -ne $null })) {
    if ($m.labels) {
        $allLabels += $m.labels
    }
}
$labelsNorm = $allLabels | ForEach-Object { $_.ToString().ToLower() }

$hasImage = $labelsNorm -contains "image"
$hasEdit = $labelsNorm -contains "edit"
$hasTts = ($labelsNorm -contains "tts") -or ($labelsNorm -contains "speech")
$hasStt = ($labelsNorm -contains "audio") -or ($labelsNorm -contains "transcription")
$hasVisionOrTool = ($labelsNorm -contains "vision") -or ($labelsNorm -contains "tool-calling")

$chatOk = Invoke-EndpointProbe "/v1/chat/completions"
$imgGenOk = Invoke-EndpointProbe "/v1/images/generations"
$imgEditOk = Invoke-EndpointProbe "/v1/images/edits"
$ttsOk = Invoke-EndpointProbe "/v1/audio/speech"
$sttOk = Invoke-EndpointProbe "/v1/audio/transcriptions"

$result = [ordered]@{
    base_url = $BaseUrl
    discovered_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    endpoints = [ordered]@{
        chat_completions = $chatOk
        images_generations = $imgGenOk
        images_edits = $imgEditOk
        audio_speech = $ttsOk
        audio_transcriptions = $sttOk
    }
    labels = [ordered]@{
        image = $hasImage
        edit = $hasEdit
        tts_or_speech = $hasTts
        audio_or_transcription = $hasStt
        vision_or_tool_calling = $hasVisionOrTool
    }
    model_count = @($models.data).Count
    models = $models.data
    omni_router_ready = ($chatOk -and $imgGenOk -and $imgEditOk -and $ttsOk -and $sttOk -and $hasImage -and $hasTts -and $hasStt)
}

$result | ConvertTo-Json -Depth 12 | Set-Content -Path $OutFile -Encoding UTF8
Write-Output ("[ok] Capability report written to: " + $OutFile)
Get-Content -Path $OutFile
