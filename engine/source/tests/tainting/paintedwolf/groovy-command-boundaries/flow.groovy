def data = [command: source(), safe: 'safe']
// ruleid: flow
sink data['command']
sink data['safe']
// ruleid: flow
sink(data['command'])
sink(data['safe'])
// ruleid: flow
sink data['command'], 'safe'
sink data['safe'], source()
// ruleid: flow
sink /* argument */ data['command']
sink 'safe'
// ruleid: flow
sink data['command'].trim()
sink data['safe'].trim()
// ruleid: flow
sink data
['safe']
sink 'safe'
[command: source()]
