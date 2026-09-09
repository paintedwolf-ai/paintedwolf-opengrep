$value = Read-Input
# ruleid: flow
Write-Output "prefix $value suffix"
Write-Output "other $value suffix"
Write-Output "prefix $value other"
Write-Output 'prefix $value suffix'
Write-Output "prefix `$value suffix"
