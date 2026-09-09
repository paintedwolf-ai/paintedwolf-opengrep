const outer=(value)=>{
const handler=()=>{
// ruleid: flow
sink(value);
};
handler();
};
export default bind(outer);
