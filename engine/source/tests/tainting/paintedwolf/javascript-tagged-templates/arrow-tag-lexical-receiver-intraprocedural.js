const factory={command:source(),make(){return (strings,value)=>this.command;}};
const tag=factory.make();
const other={command:"fixed",tag};
// ruleid: flow
sink(other.tag`fixed`);
