const factory={command:"fixed",make(){return function(strings,value){return this.command;};}};
const tag=factory.make();
const other={command:source(),tag};
// ruleid: flow
sink(other.tag`fixed`);
