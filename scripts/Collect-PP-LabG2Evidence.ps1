#Requires -Version 7.0

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Wi-Fi', 'mobile')]
    [string]$NetworkClass,

    [Parameter(Mandatory)]
    [ValidateRange(1, 3)]
    [int]$Repetition,

    [Parameter(Mandatory)]
    [ValidateSet('Baseline', 'PostRestart', 'PostRestore', 'Regression')]
    [string]$Phase,

    [uri[]]$HttpEndpoints = @(
        'http://example.com/'
        'http://neverssl.com/'
    ),

    [uri[]]$HttpsEndpoints = @(
        'https://example.com/'
        'https://www.cloudflare.com/cdn-cgi/trace'
    ),

    [uri[]]$ExitIpEndpoints = @(
        'https://api.ipify.org/'
        'https://checkip.amazonaws.com/'
    ),

    [string[]]$DnsNames = @(
        'example.com'
        'cloudflare.com'
    ),

    [System.Security.SecureString]$ExpectedExitIp,

    [switch]$PromptForExpectedExitIp,

    [ValidateSet('PASS', 'FAIL', 'NOT_TESTED')]
    [string]$DnsLeakVerdict = 'NOT_TESTED',

    [ValidatePattern('^[A-Za-z0-9._-]{1,80}$')]
    [string]$DnsLeakEvidenceId,

    [switch]$CleanReconnectConfirmed,

    [switch]$RestartPerformedConfirmed,

    [switch]$IsolationCyclePerformedConfirmed,

    [ValidatePattern('^[\p{L}\p{N} ._+()/\-]{1,100}$')]
    [string]$ClientSoftwareVersion = 'unknown',

    [ValidatePattern('^[\p{L}\p{N} ._+()/\-]{1,100}$')]
    [string]$ServerSoftwareVersion = 'unknown',

    [ValidatePattern('^(unknown|[A-Fa-f0-9]{32,128})$')]
    [string]$ServerArtifactChecksum = 'unknown',

    [uri]$HttpProxyUri,

    [ValidateRange(3, 120)]
    [int]$TimeoutSec = 20,

    [string]$EvidenceRoot = (Join-Path $env:LOCALAPPDATA 'PrivatPirat-Lab\Evidence')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$CollectorVersion = '1.0.0'

function Get-SanitizedError {
    param([AllowNull()][string]$Message)

    if ([string]::IsNullOrWhiteSpace($Message)) {
        return 'unknown error'
    }

    $Safe = $Message

    if ($env:USERPROFILE) {
        $Safe = $Safe.Replace(
            $env:USERPROFILE,
            '%USERPROFILE%',
            [StringComparison]::OrdinalIgnoreCase
        )
    }

    $Safe = $Safe -replace '(?i)https?://\S+', '[URI REDACTED]'
    $Safe = $Safe -replace '\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP REDACTED]'
    $Safe = $Safe -replace '(?i)(?<![0-9a-f:])(?:[0-9a-f]{1,4}:){2,7}[0-9a-f:]{0,4}(?![0-9a-f:])', '[IP REDACTED]'
    $Safe = $Safe -replace '(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\b', '[HOST REDACTED]'
    $Safe = $Safe -replace '(?i)\b[A-Z]:\\[^\r\n]*', '[PATH REDACTED]'
    $Safe = $Safe -replace '\\\\[^\\\s]+\\[^\r\n]*', '[PATH REDACTED]'
    $Safe = $Safe -replace '\b[0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\b', '[UUID REDACTED]'
    $Safe = $Safe -replace '\b[A-Za-z0-9_+/=-]{32,}\b', '[TOKEN REDACTED]'
    $Safe = ($Safe -replace '[\r\n]+', ' ').Trim()

    if ($Safe.Length -gt 240) {
        $Safe = $Safe.Substring(0, 240) + '...'
    }

    return $Safe
}

function ConvertFrom-SecureValue {
    param([Parameter(Mandatory)][System.Security.SecureString]$Value)

    $Pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)

    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer)
    }
}

function Test-GitAncestor {
    param([Parameter(Mandatory)][string]$Path)

    $Directory = [IO.DirectoryInfo]::new([IO.Path]::GetFullPath($Path))

    while ($null -ne $Directory) {
        if (Test-Path -LiteralPath (Join-Path $Directory.FullName '.git')) {
            return $true
        }

        $Directory = $Directory.Parent
    }

    return $false
}

function Assert-EndpointSet {
    param(
        [Parameter(Mandatory)][uri[]]$Endpoints,
        [Parameter(Mandatory)][string]$RequiredScheme,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][int]$MinimumCount
    )

    if ($Endpoints.Count -lt $MinimumCount) {
        throw "${Name}: требуется минимум $MinimumCount endpoint."
    }

    foreach ($Endpoint in $Endpoints) {
        if (-not $Endpoint.IsAbsoluteUri -or $Endpoint.Scheme -ne $RequiredScheme) {
            throw "${Name}: каждый endpoint должен иметь схему $RequiredScheme."
        }

        if ($Endpoint.UserInfo -or $Endpoint.Query -or $Endpoint.Fragment) {
            throw "${Name}: userinfo, query и fragment запрещены, чтобы не сохранить секрет."
        }
    }
}

function New-RequestParameters {
    param([Parameter(Mandatory)][uri]$Uri)

    $Parameters = @{
        Uri                 = $Uri
        Method              = 'Get'
        TimeoutSec          = $TimeoutSec
        MaximumRedirection  = 5
        SkipHttpErrorCheck  = $true
        ErrorAction         = 'Stop'
        Headers             = @{ 'User-Agent' = 'PrivatPirat-Lab-G2-Evidence/1.0' }
    }

    if ($null -ne $HttpProxyUri) {
        $Parameters.Proxy = $HttpProxyUri
    }

    return $Parameters
}

function Invoke-ResourceProbe {
    param(
        [Parameter(Mandatory)][uri]$Uri,
        [Parameter(Mandatory)][string]$Label
    )

    $Timer = [Diagnostics.Stopwatch]::StartNew()

    try {
        $RequestParameters = New-RequestParameters -Uri $Uri
        $Response = Invoke-WebRequest @RequestParameters
        $Timer.Stop()

        $StatusCode = [int]$Response.StatusCode
        $BodyLength = if ($null -eq $Response.Content) {
            0
        }
        else {
            [Text.Encoding]::UTF8.GetByteCount([string]$Response.Content)
        }

        $FinalScheme = try {
            $Response.BaseResponse.RequestMessage.RequestUri.Scheme
        }
        catch {
            $Uri.Scheme
        }

        $Passed = (
            $StatusCode -ge 200 -and
            $StatusCode -lt 400 -and
            $BodyLength -gt 0 -and
            $FinalScheme -eq $Uri.Scheme
        )

        return [pscustomobject]@{
            endpoint       = $Label
            scheme         = $Uri.Scheme
            status         = $StatusCode
            body_nonempty  = ($BodyLength -gt 0)
            same_scheme    = ($FinalScheme -eq $Uri.Scheme)
            duration_ms    = [int]$Timer.ElapsedMilliseconds
            verdict        = if ($Passed) { 'PASS' } else { 'FAIL' }
            error          = $null
        }
    }
    catch {
        $Timer.Stop()

        return [pscustomobject]@{
            endpoint       = $Label
            scheme         = $Uri.Scheme
            status         = $null
            body_nonempty  = $false
            same_scheme    = $false
            duration_ms    = [int]$Timer.ElapsedMilliseconds
            verdict        = 'FAIL'
            error          = Get-SanitizedError $_.Exception.Message
        }
    }
}

function Invoke-ExitIpProbe {
    param(
        [Parameter(Mandatory)][uri]$Uri,
        [Parameter(Mandatory)][string]$Label,
        [AllowNull()][Net.IPAddress]$ExpectedAddress
    )

    $Timer = [Diagnostics.Stopwatch]::StartNew()

    try {
        $RequestParameters = New-RequestParameters -Uri $Uri
        $Response = Invoke-WebRequest @RequestParameters
        $Timer.Stop()

        $StatusCode = [int]$Response.StatusCode
        $Content = [string]$Response.Content
        $ObservedAddress = $null

        foreach ($Candidate in @($Content -split '[^0-9A-Fa-f:.]+')) {
            if ($Candidate -notmatch '[.:]') {
                continue
            }

            $Parsed = $null

            if ([Net.IPAddress]::TryParse($Candidate, [ref]$Parsed)) {
                $ObservedAddress = $Parsed
                break
            }
        }

        $RequestPassed = (
            $StatusCode -ge 200 -and
            $StatusCode -lt 400 -and
            $null -ne $ObservedAddress
        )

        $MatchesExpected = if ($null -eq $ExpectedAddress) {
            $null
        }
        else {
            $RequestPassed -and $ObservedAddress.Equals($ExpectedAddress)
        }

        $ProbeVerdict = if (-not $RequestPassed) {
            'FAIL'
        }
        elseif ($null -eq $ExpectedAddress) {
            'PARTIAL'
        }
        elseif ($MatchesExpected) {
            'PASS'
        }
        else {
            'FAIL'
        }

        return [pscustomobject]@{
            Public = [pscustomobject]@{
                endpoint          = $Label
                status            = $StatusCode
                ip_detected       = ($null -ne $ObservedAddress)
                matches_expected  = $MatchesExpected
                duration_ms       = [int]$Timer.ElapsedMilliseconds
                verdict           = $ProbeVerdict
                error             = $null
            }
            ObservedAddress = $ObservedAddress
        }
    }
    catch {
        $Timer.Stop()

        return [pscustomobject]@{
            Public = [pscustomobject]@{
                endpoint          = $Label
                status            = $null
                ip_detected       = $false
                matches_expected  = $null
                duration_ms       = [int]$Timer.ElapsedMilliseconds
                verdict           = 'FAIL'
                error             = Get-SanitizedError $_.Exception.Message
            }
            ObservedAddress = $null
        }
    }
}

function Invoke-DnsProbe {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Label
    )

    $Timer = [Diagnostics.Stopwatch]::StartNew()

    try {
        $DnsTask = [Net.Dns]::GetHostAddressesAsync($Name)
        $TimedDnsTask = $DnsTask.WaitAsync([TimeSpan]::FromSeconds($TimeoutSec))
        $Addresses = $TimedDnsTask.GetAwaiter().GetResult()

        $Timer.Stop()

        return [pscustomobject]@{
            query          = $Label
            answer_count   = @($Addresses).Count
            has_ipv4       = (@($Addresses | Where-Object AddressFamily -eq 'InterNetwork').Count -gt 0)
            has_ipv6       = (@($Addresses | Where-Object AddressFamily -eq 'InterNetworkV6').Count -gt 0)
            duration_ms    = [int]$Timer.ElapsedMilliseconds
            verdict        = if (@($Addresses).Count -gt 0) { 'PASS' } else { 'FAIL' }
            error          = $null
        }
    }
    catch {
        $Timer.Stop()

        return [pscustomobject]@{
            query          = $Label
            answer_count   = 0
            has_ipv4       = $false
            has_ipv6       = $false
            duration_ms    = [int]$Timer.ElapsedMilliseconds
            verdict        = 'FAIL'
            error          = Get-SanitizedError $_.Exception.Message
        }
    }
}

try {
    Assert-EndpointSet -Endpoints $HttpEndpoints -RequiredScheme 'http' `
        -Name 'HTTP' -MinimumCount 1
    Assert-EndpointSet -Endpoints $HttpsEndpoints -RequiredScheme 'https' `
        -Name 'HTTPS' -MinimumCount 1
    Assert-EndpointSet -Endpoints $ExitIpEndpoints -RequiredScheme 'https' `
        -Name 'Exit-IP' -MinimumCount 2

    $ResourceHostCount = @(
        @($HttpEndpoints + $HttpsEndpoints) |
            ForEach-Object { $_.DnsSafeHost.ToLowerInvariant() } |
            Select-Object -Unique
    ).Count

    if ($ResourceHostCount -lt 2) {
        throw 'HTTP/HTTPS: требуются как минимум два независимых host.'
    }

    $ExitHostCount = @(
        $ExitIpEndpoints |
            ForEach-Object { $_.DnsSafeHost.ToLowerInvariant() } |
            Select-Object -Unique
    ).Count

    if ($ExitHostCount -lt 2) {
        throw 'Exit-IP: два endpoint должны принадлежать разным host.'
    }

    if ($DnsNames.Count -lt 2) {
        throw 'DNS: требуются как минимум два имени для проверки разрешения.'
    }

    foreach ($DnsName in $DnsNames) {
        if ([Uri]::CheckHostName($DnsName) -ne [UriHostNameType]::Dns) {
            throw 'DNS: каждое значение должно быть DNS-именем, а не IP или URI.'
        }
    }

    if ($null -ne $HttpProxyUri) {
        if (
            -not $HttpProxyUri.IsAbsoluteUri -or
            $HttpProxyUri.Scheme -notin @('http', 'https') -or
            $HttpProxyUri.UserInfo -or
            $HttpProxyUri.Query -or
            $HttpProxyUri.Fragment
        ) {
            throw 'HttpProxyUri должен быть безопасным абсолютным HTTP(S) URI без credentials и query.'
        }
    }

    if ($DnsLeakVerdict -ne 'NOT_TESTED' -and -not $DnsLeakEvidenceId) {
        throw 'Для DNS leak verdict PASS/FAIL требуется DnsLeakEvidenceId.'
    }

    if ($Phase -eq 'PostRestart' -and -not $RestartPerformedConfirmed) {
        throw 'Phase=PostRestart требует RestartPerformedConfirmed.'
    }

    if ($Phase -eq 'PostRestore' -and -not $IsolationCyclePerformedConfirmed) {
        throw 'Phase=PostRestore требует IsolationCyclePerformedConfirmed.'
    }

    if (Test-GitAncestor -Path $EvidenceRoot) {
        throw 'EvidenceRoot находится внутри Git worktree. Выберите приватный каталог вне репозитория.'
    }

    if ($PromptForExpectedExitIp -and $null -ne $ExpectedExitIp) {
        throw 'Используйте либо ExpectedExitIp, либо PromptForExpectedExitIp, но не оба параметра.'
    }

    if ($PromptForExpectedExitIp) {
        Write-Host 'Введите ожидаемый exit IP. Значение скрыто и не записывается.' `
            -ForegroundColor Cyan
        $ExpectedExitIp = Read-Host 'Expected exit IP' -AsSecureString
    }

    $ExpectedAddress = $null

    if ($null -ne $ExpectedExitIp) {
        $ExpectedText = (ConvertFrom-SecureValue -Value $ExpectedExitIp).Trim()

        if (-not [Net.IPAddress]::TryParse($ExpectedText, [ref]$ExpectedAddress)) {
            throw 'Ожидаемый exit IP имеет неверный формат.'
        }

        Remove-Variable ExpectedText -ErrorAction SilentlyContinue
    }

    $UtcNow = [DateTimeOffset]::UtcNow
    $NetworkSlug = if ($NetworkClass -eq 'Wi-Fi') { 'wifi' } else { 'mobile' }
    $EvidenceId = 'PP-LAB-I-{0}-{1}-R{2}-{3}' -f `
        $UtcNow.ToString('yyyyMMddTHHmmssfffZ'),
        $NetworkSlug,
        $Repetition,
        $Phase.ToLowerInvariant()

    $RunDirectory = Join-Path $EvidenceRoot $EvidenceId

    if (Test-Path -LiteralPath $RunDirectory) {
        throw 'Каталог evidence уже существует. Перезапись запрещена.'
    }

    New-Item -ItemType Directory -Path $RunDirectory | Out-Null

    Write-Host "Собираю санитизированное evidence: $EvidenceId" -ForegroundColor Green

    $HttpResults = @()
    $Index = 0
    foreach ($Endpoint in $HttpEndpoints) {
        $Index++
        $HttpResults += Invoke-ResourceProbe -Uri $Endpoint -Label "http-$Index"
    }

    $HttpsResults = @()
    $Index = 0
    foreach ($Endpoint in $HttpsEndpoints) {
        $Index++
        $HttpsResults += Invoke-ResourceProbe -Uri $Endpoint -Label "https-$Index"
    }

    $ExitInternalResults = @()
    $Index = 0
    foreach ($Endpoint in $ExitIpEndpoints) {
        $Index++
        $ExitInternalResults += Invoke-ExitIpProbe -Uri $Endpoint `
            -Label "exit-ip-$Index" -ExpectedAddress $ExpectedAddress
    }

    $DnsResults = @()
    $Index = 0
    foreach ($DnsName in $DnsNames) {
        $Index++
        $DnsResults += Invoke-DnsProbe -Name $DnsName -Label "dns-$Index"
    }

    $HttpPass = (@($HttpResults | Where-Object verdict -ne 'PASS').Count -eq 0)
    $HttpsPass = (@($HttpsResults | Where-Object verdict -ne 'PASS').Count -eq 0)
    $DnsResolutionPass = (@($DnsResults | Where-Object verdict -ne 'PASS').Count -eq 0)

    $ObservedAddresses = @(
        $ExitInternalResults |
            Where-Object { $null -ne $_.ObservedAddress } |
            ForEach-Object { $_.ObservedAddress.ToString() }
    )

    $ExitServicesAgree = (
        $ObservedAddresses.Count -eq $ExitIpEndpoints.Count -and
        @($ObservedAddresses | Select-Object -Unique).Count -eq 1
    )

    $ExitMatchTested = ($null -ne $ExpectedAddress)

    $ExitMatchesExpected = if ($ExitMatchTested) {
        @($ExitInternalResults | Where-Object { -not $_.Public.matches_expected }).Count -eq 0
    }
    else {
        $null
    }

    $DirectFailure = (
        -not $HttpPass -or
        -not $HttpsPass -or
        -not $DnsResolutionPass -or
        -not $ExitServicesAgree -or
        ($ExitMatchTested -and -not $ExitMatchesExpected) -or
        $DnsLeakVerdict -eq 'FAIL'
    )

    $ObservationVerdict = if ($DirectFailure) {
        'FAIL'
    }
    elseif (
        $CleanReconnectConfirmed -and
        $DnsLeakVerdict -eq 'PASS' -and
        $ExitMatchTested
    ) {
        'PASS'
    }
    else {
        'PARTIAL'
    }

    $G2Verdict = if ($ObservationVerdict -eq 'FAIL') {
        'FAIL'
    }
    else {
        'PARTIAL'
    }

    $RemainingGates = [Collections.Generic.List[string]]::new()
    [void]$RemainingGates.Add('aggregate three clean reconnect repetitions per available target network')
    [void]$RemainingGates.Add('verify server-unit restart recovery as a separate approved gate')
    [void]$RemainingGates.Add('verify route stop/start isolation as a separate approved gate')
    [void]$RemainingGates.Add('verify every other available target network')

    if (-not $CleanReconnectConfirmed) {
        [void]$RemainingGates.Add('confirm that this observation followed a clean client reconnect')
    }

    if ($DnsLeakVerdict -ne 'PASS') {
        [void]$RemainingGates.Add('attach an independent DNS leak assessment')
    }

    if (-not $ExitMatchTested) {
        [void]$RemainingGates.Add('compare both exit-IP observations with the approved server exit IP')
    }

    $CollectorHash = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()

    $Evidence = [ordered]@{
        evidence_schema = 'pp-lab-g2-client-v1'
        evidence_id = $EvidenceId
        utc_timestamp = $UtcNow.ToString('o')
        collector_version = $CollectorVersion
        collector_sha256 = $CollectorHash
        powershell_version = $PSVersionTable.PSVersion.ToString()
        classification = 'FACT'
        route = 'PP-LAB-I'
        network_class = $NetworkClass
        phase = $Phase
        repetition = $Repetition
        client_software_version = $ClientSoftwareVersion
        server_software_version = $ServerSoftwareVersion
        server_artifact_checksum = $ServerArtifactChecksum.ToLowerInvariant()
        clean_reconnect_confirmed = [bool]$CleanReconnectConfirmed
        restart_performed_confirmed = [bool]$RestartPerformedConfirmed
        isolation_cycle_performed_confirmed = [bool]$IsolationCyclePerformedConfirmed
        proxy_supplied = ($null -ne $HttpProxyUri)
        endpoint_independence = [ordered]@{
            resource_host_count = $ResourceHostCount
            exit_ip_host_count = $ExitHostCount
        }
        dns = [ordered]@{
            resolution_verdict = if ($DnsResolutionPass) { 'PASS' } else { 'FAIL' }
            leak_verdict = $DnsLeakVerdict
            leak_evidence_id = $DnsLeakEvidenceId
            observations = $DnsResults
        }
        http = [ordered]@{
            verdict = if ($HttpPass) { 'PASS' } else { 'FAIL' }
            observations = $HttpResults
        }
        https = [ordered]@{
            verdict = if ($HttpsPass) { 'PASS' } else { 'FAIL' }
            observations = $HttpsResults
        }
        exit_ip = [ordered]@{
            services_agree = $ExitServicesAgree
            match_tested = $ExitMatchTested
            matches_expected = $ExitMatchesExpected
            raw_addresses_stored = $false
            observations = @($ExitInternalResults | ForEach-Object { $_.Public })
        }
        observation_verdict = $ObservationVerdict
        g2_verdict = $G2Verdict
        remaining_gates = @($RemainingGates)
    }

    $JsonPath = Join-Path $RunDirectory 'evidence.json'
    $TextPath = Join-Path $RunDirectory 'summary.txt'
    $HashPath = Join-Path $RunDirectory 'evidence.sha256'
    $HandoffPath = Join-Path $RunDirectory 'handoff.txt'

    $Evidence | ConvertTo-Json -Depth 10 |
        Set-Content -LiteralPath $JsonPath -Encoding utf8

    $JsonHash = (Get-FileHash -LiteralPath $JsonPath -Algorithm SHA256).Hash.ToLowerInvariant()

    "$JsonHash *evidence.json" |
        Set-Content -LiteralPath $HashPath -Encoding ascii

    $ExitMatchSummary = if ($ExitMatchTested) {
        $ExitMatchesExpected.ToString()
    }
    else {
        'NOT_TESTED'
    }

    $Summary = @(
        "Evidence ID: $EvidenceId"
        "UTC timestamp: $($UtcNow.ToString('o'))"
        'Route: PP-LAB-I'
        "Network class: $NetworkClass"
        "Phase: $Phase"
        "Repetition: $Repetition"
        "Clean reconnect: $([bool]$CleanReconnectConfirmed)"
        "DNS resolution: $($Evidence.dns.resolution_verdict)"
        "DNS leak: $DnsLeakVerdict"
        "HTTP: $($Evidence.http.verdict)"
        "HTTPS: $($Evidence.https.verdict)"
        "Exit-IP services agree: $ExitServicesAgree"
        "Exit-IP match: $ExitMatchSummary"
        "Observation verdict: $ObservationVerdict"
        "G2 verdict: $G2Verdict"
        'Raw exit IP stored: false'
        "Evidence JSON SHA-256: $JsonHash"
        'Remaining gates:'
        @($RemainingGates | ForEach-Object { "- $_" })
    )

    $Summary | Set-Content -LiteralPath $TextPath -Encoding utf8

    @(
        '===== SUMMARY ====='
        (Get-Content -LiteralPath $TextPath -Raw)
        '===== EVIDENCE JSON ====='
        (Get-Content -LiteralPath $JsonPath -Raw)
        '===== EVIDENCE SHA-256 ====='
        (Get-Content -LiteralPath $HashPath -Raw)
    ) | Set-Content -LiteralPath $HandoffPath -Encoding utf8

    Write-Host "`n===== НАБЛЮДЕНИЕ ЗАВЕРШЕНО =====" -ForegroundColor Green
    Write-Host "OBSERVATION_VERDICT=$ObservationVerdict"
    Write-Host "G2_VERDICT=$G2Verdict"
    Write-Host "EVIDENCE_ID=$EvidenceId" -ForegroundColor Cyan
    Write-Host 'HANDOFF=handoff.txt' -ForegroundColor Cyan
    Write-Host 'Сырые IP, URI, ответы endpoint и credentials не записывались.' `
        -ForegroundColor Yellow

    $ExitCode = switch ($G2Verdict) {
        'PASS' { 0 }
        'PARTIAL' { 10 }
        'FAIL' { 20 }
        default { 30 }
    }

    exit $ExitCode
}
catch {
    $SafeError = Get-SanitizedError $_.Exception.Message
    Write-Host "STOP: $SafeError" -ForegroundColor Red
    exit 30
}
