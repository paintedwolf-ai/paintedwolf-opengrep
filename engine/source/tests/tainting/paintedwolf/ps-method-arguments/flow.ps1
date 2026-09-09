$value = Read-Input
# ruleid: flow
$api.Send($value, 'safe')
$api.Send('safe', $value)
# ruleid: flow
$api.SendSecond('safe', $value)
$api.SendSecond($value, 'safe')
# ruleid: flow
$api.Send(($value + ' suffix'), 'safe')
# ruleid: flow
$api.Send($helper.Transform($value), 'safe')
$api.Send($helper.Transform('safe'), $value)
$api.Send()
$values = $value, 'safe'
# ruleid: flow
$api.Send($values[0], 'safe')
$api.Send($values[1], $value)
$values[0] = 'fixed'
$api.Send($values[0], $value)
# ruleid: flow
$api.Send(($value, 'safe'), 'safe')
$api.Send(('safe', 'fixed'), $value)
# ruleid: flow
$api.sEnD($value, 'safe')
