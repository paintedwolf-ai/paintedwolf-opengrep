const object={command:source(),tag(strings,value){this.command="fixed";return "fixed";}};
object.tag`fixed`;
// ok: flow
sink(object.command);
