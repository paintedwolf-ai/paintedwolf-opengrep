const factory={command:"fixed",make(){return (strings,value)=>this.command;}};
const tag=factory.make();
const other={command:source(),tag};
// ok: flow
sink(other.tag`fixed`);
