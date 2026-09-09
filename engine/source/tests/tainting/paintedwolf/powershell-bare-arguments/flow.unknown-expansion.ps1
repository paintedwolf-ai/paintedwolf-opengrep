$value = Read-Input
Write-Output prefix$value
# ruleid: flow
Invoke-PwAuditSink $value
