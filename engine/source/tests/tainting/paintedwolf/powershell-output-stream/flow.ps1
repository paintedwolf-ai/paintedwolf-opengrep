function Get-Direct {
  Invoke-RestMethod 'https://example.test'
}
# ruleid: flow
Invoke-Expression (Get-Direct)
function Get-Value {
  $value = Invoke-RestMethod 'https://example.test'
  $value
  'safe'
}
# ruleid: flow
Invoke-Expression (Get-Value)
function Get-Early {
  Invoke-RestMethod 'https://example.test'
  return 'safe'
}
# ruleid: flow
Invoke-Expression (Get-Early)
function Get-BareReturn {
  Invoke-RestMethod 'https://example.test'
  return
}
# ruleid: flow
Invoke-Expression (Get-BareReturn)
function Get-Safe {
  $value = Invoke-RestMethod 'https://example.test'
  'safe'
}
Invoke-Expression (Get-Safe)
function Get-Unreachable {
  return 'safe'
  Invoke-RestMethod 'https://example.test'
}
Invoke-Expression (Get-Unreachable)
