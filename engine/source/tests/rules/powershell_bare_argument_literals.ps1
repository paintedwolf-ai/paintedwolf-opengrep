# ruleid: bare-argument
Write-Output FixedCase
# ruleid: bare-argument
write-output "FixedCase"
# ruleid: bare-argument
WRITE-OUTPUT 'FixedCase'
# ok: bare-argument
Write-Output fixedcase
# ok: bare-argument
Write-Output 'Write-Output FixedCase'
# ok: bare-argument
Write-Output '$value'
