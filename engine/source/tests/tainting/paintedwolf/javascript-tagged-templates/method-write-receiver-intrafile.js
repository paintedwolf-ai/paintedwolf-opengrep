const object={command:"fixed",tag(strings,value){this.command=value; return "fixed";}};
object.tag`${source()}`;
// ruleid: flow
sink(object.command);
