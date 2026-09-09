$value = Invoke-WebRequest $uri
# ruleid: flow
Invoke-Expression "prefix $value"
Invoke-Expression '$value'
