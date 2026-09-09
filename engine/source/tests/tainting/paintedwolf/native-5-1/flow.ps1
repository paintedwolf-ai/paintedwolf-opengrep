# ruleid: flow
Invoke-WebRequest $uri | Invoke-Expression
Write-Output "fixed" | Invoke-Expression
