$value = Read-Input
Write-Output FixedCase
Write-Output escaped` value
Write-Output 'Read-Input'
# ruleid: flow
Invoke-PwAuditSink $value
Invoke-PwAuditSink FixedCase
