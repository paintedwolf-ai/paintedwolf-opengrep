function select() {
  function arguments() { return 'safe'; }
  return arguments();
}
// ok: flow
sink(select(source()));
