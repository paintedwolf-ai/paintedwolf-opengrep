const object={command:"fixed",tag(strings,value){return this.command;}};
// ok: flow
sink(object.tag`${source()}`);
