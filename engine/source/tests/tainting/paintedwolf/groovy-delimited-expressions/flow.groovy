def data = [command: source(), safe: 'safe']
// ruleid: flow
sink(data[
  'command'
])
sink(data[
  'safe'
])
// ruleid: flow
sink([
  source()
])
sink [
  source()
]
// ruleid: flow
sink([key:
  source()
])
sink([key:
  'safe'
])
