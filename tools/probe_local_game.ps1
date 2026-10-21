# 스타세이비어가 설치된 PC 에서 «읽기만» 해서, 내 정보를 불러올 통로가 있는지 살펴보는 점검 스크립트.
# - 게임 파일·통신은 건드리지 않는다(파일 목록 + 기록 파일 안의 웹 주소만 본다).
# - 보고서에는 인증 열쇠가 남지 않게 주소의 ?뒤 값·긴 토큰 조각을 가린다.
# 사용: powershell -ExecutionPolicy Bypass -File tools\probe_local_game.ps1
#       (게임에서 뽑기 기록·공지 같은 웹 화면을 한 번 연 «뒤에» 실행해야 주소가 남아 있다)
param(
    [string[]]$ExtraPath = @(),
    [string]$OutDir = (Join-Path $PSScriptRoot '..\local\probe'),
    [int]$MaxMB = 64,
    [int]$MaxFiles = 6000
)
$ErrorActionPreference = 'SilentlyContinue'
$pat = 'star\s*savior|starsavior|스타\s*세이비어|bside'
$home_ = $env:USERPROFILE

function Hide-Home([string]$p) { if ($home_) { return $p.Replace($home_, '%USERPROFILE%') } else { return $p } }

# 주소에서 인증 값이 될 만한 것을 전부 가린다: ?·# 뒤 값, 길게 이어진 영숫자 조각
function Mask-Url([string]$u) {
    $u = $u.TrimEnd('.', ',', ')', ']', "'", '"', ';')
    $frag = ''
    $i = $u.IndexOf('#'); if ($i -ge 0) { $frag = '#***'; $u = $u.Substring(0, $i) }
    $q = ''
    $i = $u.IndexOf('?')
    if ($i -ge 0) {
        $keys = $u.Substring($i + 1).Split('&') | ForEach-Object { ($_ -split '=', 2)[0] } | Where-Object { $_ }
        $q = '?' + (($keys | ForEach-Object { "$_=***" }) -join '&')
        $u = $u.Substring(0, $i)
    }
    $u = [regex]::Replace($u, '[A-Za-z0-9_\-]{24,}', { param($m) "<$($m.Value.Length)자>" })
    return $u + $q + $frag
}

# 1) 후보 폴더 모으기 ------------------------------------------------------
$cands = New-Object System.Collections.Generic.List[object]
function Add-Cand([string]$path, [string]$why) {
    if ($path -and (Test-Path -LiteralPath $path)) {
        $full = (Resolve-Path -LiteralPath $path).Path
        if (-not ($cands | Where-Object { $_.Path -eq $full })) { $cands.Add([pscustomobject]@{ Path = $full; Why = $why }) }
    }
}

foreach ($base in @("$home_\AppData\LocalLow", "$home_\AppData\Local", "$home_\AppData\Roaming")) {
    Get-ChildItem -LiteralPath $base -Directory | ForEach-Object {
        if ($_.Name -match $pat) { Add-Cand $_.FullName "앱 데이터($($_.Name))" }
    }
}
# 개발사 폴더 아래 하위 게임 폴더(카운터사이드 등 다른 게임도 같이 나온다 — 보고서에서 구분)
Get-ChildItem -LiteralPath "$home_\AppData\LocalLow\studioBside" -Directory | ForEach-Object { Add-Cand $_.FullName "개발사 폴더\$($_.Name)" }

# Steam 라이브러리
$steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam').SteamPath
$libs = @()
if ($steam) {
    $libs += $steam
    $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
    if (Test-Path $vdf) {
        Select-String -Path $vdf -Pattern '"path"\s+"([^"]+)"' | ForEach-Object { $libs += $_.Matches[0].Groups[1].Value.Replace('\\', '\') }
    }
}
foreach ($lib in ($libs | Select-Object -Unique)) {
    $sa = Join-Path $lib 'steamapps'
    Get-ChildItem -LiteralPath $sa -Filter 'appmanifest_*.acf' | ForEach-Object {
        $t = Get-Content -LiteralPath $_.FullName -Raw
        if ($t -match '"name"\s+"([^"]+)"' -and $Matches[1] -match $pat) {
            $nm = $Matches[1]
            if ($t -match '"installdir"\s+"([^"]+)"') { Add-Cand (Join-Path $sa "common\$($Matches[1])") "Steam 설치($nm)" }
        }
    }
    Get-ChildItem -LiteralPath (Join-Path $sa 'common') -Directory | Where-Object { $_.Name -match $pat } | ForEach-Object { Add-Cand $_.FullName 'Steam 폴더 이름' }
}

# 프로그램 추가/제거 목록(전용 런처·스토어 설치)
foreach ($k in @('HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
                 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
                 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*')) {
    Get-ItemProperty $k | Where-Object { $_.DisplayName -match $pat } | ForEach-Object { Add-Cand $_.InstallLocation "설치 목록($($_.DisplayName))" }
}
foreach ($p in $ExtraPath) { Add-Cand $p '직접 지정' }

# 다른 후보 폴더 안에 든 폴더는 빼서 같은 파일을 두 번 읽지 않는다
$cands = @($cands | Where-Object { $c = $_; -not ($cands | Where-Object { $c.Path.StartsWith($_.Path + [IO.Path]::DirectorySeparatorChar) }) })

# 2) 파일 목록 + 주소 찾기 --------------------------------------------------
$urlRe = [regex]'https?://[A-Za-z0-9\-._~:/?#\[\]@!$&''()*+,;=%]{6,}'
$hot = 'gacha|recruit|summon|history|record|log|webview|auth|token|profile|user|account|api'
$urls = @{}
$sections = @()
$scanned = 0; $skipped = 0

foreach ($c in $cands) {
    $files = @(Get-ChildItem -LiteralPath $c.Path -Recurse -File -Force)
    $totalMB = [math]::Round((($files | Measure-Object Length -Sum).Sum) / 1MB, 1)
    $logs = $files | Where-Object { $_.Name -match '\.(log|txt|json|xml|ini|cfg)$' -or $_.Name -match '^Player' } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 40
    $recent = $files | Sort-Object LastWriteTime -Descending | Select-Object -First 25
    $lines = @("### $(Hide-Home $c.Path)", "- 찾은 이유: $($c.Why) · 파일 $($files.Count)개 · $totalMB MB", '', '최근 바뀐 파일 25개:', '')
    $lines += $recent | ForEach-Object { "- $(Hide-Home $_.FullName.Substring($c.Path.Length)) ($([math]::Round($_.Length/1KB,1)) KB, $($_.LastWriteTime.ToString('yyyy-MM-dd HH:mm')))" }
    $lines += @('', '기록·설정 파일로 보이는 것:', '')
    $lines += $logs | ForEach-Object { "- $(Hide-Home $_.FullName.Substring($c.Path.Length)) ($([math]::Round($_.Length/1KB,1)) KB)" }
    $sections += ($lines -join "`n")

    foreach ($f in $files) {
        if ($scanned -ge $MaxFiles) { $skipped++; continue }
        if ($f.Length -gt $MaxMB * 1MB -or $f.Length -eq 0) { $skipped++; continue }
        if ($f.Extension -match '^\.(png|jpg|jpeg|ogg|wav|mp4|bank|dll|exe)$') { continue }
        $scanned++
        $bytes = [IO.File]::ReadAllBytes($f.FullName)
        $texts = @([Text.Encoding]::GetEncoding(28591).GetString($bytes))
        if ($f.Length -le 8MB) { $texts += [Text.Encoding]::Unicode.GetString($bytes) }
        foreach ($t in $texts) {
            foreach ($m in $urlRe.Matches($t)) {
                $mu = Mask-Url $m.Value
                if (-not $urls.ContainsKey($mu)) { $urls[$mu] = [pscustomobject]@{ Url = $mu; N = 0; Files = New-Object System.Collections.Generic.HashSet[string] } }
                $urls[$mu].N++
                [void]$urls[$mu].Files.Add((Hide-Home $f.FullName))
            }
        }
    }
}

# 3) 보고서 -------------------------------------------------------------------
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$out = Join-Path $OutDir ("probe_{0}.md" -f (Get-Date -Format 'yyyyMMdd_HHmm'))
$rows = $urls.Values | Sort-Object @{ e = { if ($_.Url -match $hot) { 0 } else { 1 } } }, @{ e = { -$_.N } }
$md = @(
    '# 스타세이비어 로컬 점검 보고서',
    '',
    "- 실행: $(Get-Date -Format 'yyyy-MM-dd HH:mm') · PowerShell $($PSVersionTable.PSVersion)",
    "- 후보 폴더 $($cands.Count)곳 · 읽은 파일 $($scanned)개 · 건너뜀 $($skipped)개(크기 $MaxMB MB 초과·개수 상한 $MaxFiles)",
    '- 주소의 ?·# 뒤 값과 24자 이상 토큰 조각은 가렸다(<N자>). 그래도 공유 전에 한 번 훑어볼 것.',
    '',
    '## 후보 폴더',
    ''
)
if ($cands.Count -eq 0) { $md += '- 없음 — 게임이 설치돼 있지 않거나 다른 위치. `-ExtraPath "<설치 폴더>"` 로 다시 실행.' }
$md += $cands | ForEach-Object { "- $(Hide-Home $_.Path) — $($_.Why)" }
$md += @('', '## 기록 안의 웹 주소(관심 낱말 먼저, 많이 나온 순)', '')
if (-not $rows) { $md += '- 없음' }
$md += $rows | Select-Object -First 300 | ForEach-Object {
    $flag = if ($_.Url -match $hot) { '★ ' } else { '' }
    "- $flag``$($_.Url)`` ×$($_.N) — $((@($_.Files) | Select-Object -First 3) -join ' · ')"
}
$md += @('', '## 폴더별 파일', '')
$md += $sections
[IO.File]::WriteAllText($out, ($md -join "`n"), (New-Object Text.UTF8Encoding($true)))

Write-Host "후보 폴더 $($cands.Count)곳, 웹 주소 $($urls.Count)종 (관심 낱말 ★ $(@($rows | Where-Object { $_.Url -match $hot }).Count)종)"
Write-Host "보고서: $out"
