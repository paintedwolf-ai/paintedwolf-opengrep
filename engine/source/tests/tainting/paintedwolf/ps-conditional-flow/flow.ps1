function Test-UnknownBranch($condition) {
  $value = Read-Input
  if ($condition) { $value = 'fixed' }
  # ruleid: flow
  Invoke-PwAuditSink $value
}
function Test-DefiniteOverwrite {
  $value = Read-Input
  if ($true) { $value = 'fixed' }
  Invoke-PwAuditSink $value
}
function Test-UnreachableSource {
  if ($false) { $value = Read-Input } else { $value = 'fixed' }
  Invoke-PwAuditSink $value
}
function Test-ElseIf($first, $second) {
  $value = 'fixed'
  if ($first) { $value = 'fixed' } elseif ($second) { $value = Read-Input } else { $value = 'fixed' }
  # ruleid: flow
  Invoke-PwAuditSink $value
}
function Test-ElseIfSafe($first) {
  $value = Read-Input
  if ($first) { $value = 'fixed' } elseif ($true) { $value = 'fixed' } else { $value = Read-Input }
  Invoke-PwAuditSink $value
}
function Get-ConditionalOutput($condition) {
  if ($condition) { Read-Input } else { 'fixed' }
}
# ruleid: flow
Invoke-PwAuditSink (Get-ConditionalOutput $unknown)
function Get-SafeOutput($condition) {
  if ($condition) { 'fixed' } else { 'also fixed' }
}
Invoke-PwAuditSink (Get-SafeOutput $unknown)
