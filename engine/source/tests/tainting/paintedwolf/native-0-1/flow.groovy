def value = source()
// ruleid: flow
sink("prefix ${value}")
sink('value')
