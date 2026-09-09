# café
$value = Read-Input
# ruleid: syntax-location
Invoke-PwAuditSink $value
if ($true) { Write-Output 'safe'