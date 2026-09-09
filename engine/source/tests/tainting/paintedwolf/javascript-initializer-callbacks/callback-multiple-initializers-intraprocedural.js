const first=(value)=>{
// ruleid: flow
sink(value);
};
const firstBinding=bind(first);
const second=(value)=>{
// ruleid: flow
sink(value);
};
export default bind(second);
