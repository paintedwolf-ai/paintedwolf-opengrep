$value = Read-Input
# ruleid: flow
Invoke-PwAuditSink "prefix $value suffix"
Invoke-PwAuditSink 'prefix $value suffix'
