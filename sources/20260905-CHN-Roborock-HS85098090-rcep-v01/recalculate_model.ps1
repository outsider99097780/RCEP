param(
    [string]$InputCsv = "model_inputs.csv"
)

$ErrorActionPreference = "Stop"
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$inputPath = Join-Path $base $InputCsv
$rows = Import-Csv -LiteralPath $inputPath | Where-Object {
    $_.imports_2025_usd_thousand -and
    $_.import_cagr_2020_2025_pct -and
    $_.china_share_2025_pct -and
    $_.epi_potential_usd -and
    $_.untapped_potential_usd
}

$data = foreach ($r in $rows) {
    $epi = [double]$r.epi_potential_usd
    $untapped = [double]$r.untapped_potential_usd
    [pscustomobject]@{
        country_code = $r.country_code
        country_name = $r.country_name
        market_size = [math]::Log(1 + [double]$r.imports_2025_usd_thousand)
        market_growth = [double]$r.import_cagr_2020_2025_pct
        china_share = [double]$r.china_share_2025_pct
        untapped_amount = [math]::Log(1 + $untapped)
        untapped_ratio = if ($epi -gt 0) { $untapped / $epi } else { 0 }
        imports_2025_usd_thousand = [double]$r.imports_2025_usd_thousand
        import_cagr_2020_2025_pct = [double]$r.import_cagr_2020_2025_pct
        china_share_2025_pct = [double]$r.china_share_2025_pct
        epi_potential_usd = $epi
        untapped_potential_usd = $untapped
        source_ids = $r.source_ids
    }
}

$indicators = @("market_size", "market_growth", "china_share", "untapped_amount", "untapped_ratio")
$normalized = foreach ($row in $data) {
    $out = [ordered]@{ country_code=$row.country_code; country_name=$row.country_name }
    foreach ($indicator in $indicators) {
        $vals = $data | ForEach-Object { [double]($_.$indicator) }
        $min = ($vals | Measure-Object -Minimum).Minimum
        $max = ($vals | Measure-Object -Maximum).Maximum
        $out[$indicator] = if ($max -eq $min) { 0 } else { ([double]$row.$indicator - $min) / ($max - $min) }
    }
    [pscustomobject]$out
}

$n = $normalized.Count
$k = 1 / [math]::Log($n)
$divergence = @{}
foreach ($indicator in $indicators) {
    $sum = ($normalized | Measure-Object -Property $indicator -Sum).Sum
    $entropySum = 0.0
    foreach ($row in $normalized) {
        $p = if ($sum -eq 0) { 0 } else { [double]$row.$indicator / $sum }
        if ($p -gt 0) { $entropySum += $p * [math]::Log($p) }
    }
    $entropy = -$k * $entropySum
    $divergence[$indicator] = 1 - $entropy
}
$divergenceTotal = ($indicators | ForEach-Object { $divergence[$_] } | Measure-Object -Sum).Sum
$weights = @{}
foreach ($indicator in $indicators) { $weights[$indicator] = $divergence[$indicator] / $divergenceTotal }

function Get-TopsisScores([hashtable]$WeightMap, [string]$Scenario) {
    $result = foreach ($row in $normalized) {
        $dPlus2 = 0.0
        $dMinus2 = 0.0
        foreach ($indicator in $indicators) {
            $v = [double]$row.$indicator * [double]$WeightMap[$indicator]
            $best = [double]$WeightMap[$indicator]
            $worst = 0.0
            $dPlus2 += [math]::Pow($v - $best, 2)
            $dMinus2 += [math]::Pow($v - $worst, 2)
        }
        $dPlus = [math]::Sqrt($dPlus2)
        $dMinus = [math]::Sqrt($dMinus2)
        $score = if (($dPlus + $dMinus) -eq 0) { 0 } else { $dMinus / ($dPlus + $dMinus) }
        [pscustomobject]@{ country_code=$row.country_code; country_name=$row.country_name; scenario=$Scenario; score=$score }
    }
    $rank = 0
    $result | Sort-Object score -Descending | ForEach-Object {
        $rank++
        [pscustomobject]@{ country_code=$_.country_code; country_name=$_.country_name; scenario=$_.scenario; score=[math]::Round($_.score,6); rank=$rank }
    }
}

$equalWeights = @{}
foreach ($indicator in $indicators) { $equalWeights[$indicator] = 1.0 / $indicators.Count }
$strategyWeights = @{
    market_size = 0.30
    market_growth = 0.10
    china_share = 0.10
    untapped_amount = 0.30
    untapped_ratio = 0.20
}
$entropyScores = Get-TopsisScores $weights "entropy_topsis"
$equalScores = Get-TopsisScores $equalWeights "equal_weight_topsis"
$strategyScores = Get-TopsisScores $strategyWeights "strategy_weight_topsis"

$weightRows = foreach ($indicator in $indicators) {
    [pscustomobject]@{
        indicator = $indicator
        direction = "benefit"
        transform = if ($indicator -in @("market_size", "untapped_amount")) { "ln(1+x), then min-max" } else { "min-max" }
        entropy_weight = [math]::Round($weights[$indicator],6)
        equal_weight = 0.2
        strategy_weight = $strategyWeights[$indicator]
    }
}

$ranking = foreach ($score in $strategyScores) {
    $raw = $data | Where-Object country_code -eq $score.country_code
    $equal = $equalScores | Where-Object country_code -eq $score.country_code
    $entropy = $entropyScores | Where-Object country_code -eq $score.country_code
    [pscustomobject]@{
        rank = $score.rank
        country_code = $score.country_code
        country_name = $score.country_name
        strategy_topsis_score = $score.score
        equal_weight_rank = $equal.rank
        equal_weight_score = $equal.score
        entropy_weight_rank = $entropy.rank
        entropy_topsis_score = $entropy.score
        imports_2025_usd_thousand = $raw.imports_2025_usd_thousand
        import_cagr_2020_2025_pct = $raw.import_cagr_2020_2025_pct
        china_share_2025_pct = $raw.china_share_2025_pct
        epi_potential_usd = $raw.epi_potential_usd
        untapped_potential_usd = $raw.untapped_potential_usd
        untapped_ratio = [math]::Round($raw.untapped_ratio,6)
        source_ids = $raw.source_ids
    }
}

$normalized | Export-Csv -LiteralPath (Join-Path $base "model_normalized.csv") -NoTypeInformation -Encoding UTF8
$weightRows | Export-Csv -LiteralPath (Join-Path $base "model_weights.csv") -NoTypeInformation -Encoding UTF8
$ranking | Export-Csv -LiteralPath (Join-Path $base "market_ranking_recalculated.csv") -NoTypeInformation -Encoding UTF8
@($strategyScores + $equalScores + $entropyScores) | Export-Csv -LiteralPath (Join-Path $base "sensitivity_results.csv") -NoTypeInformation -Encoding UTF8

$ranking | Format-Table rank,country_name,strategy_topsis_score,equal_weight_rank,entropy_weight_rank -AutoSize
