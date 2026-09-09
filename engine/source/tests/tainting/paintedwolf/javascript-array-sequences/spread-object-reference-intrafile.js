const input=[{value:'fixed'}];
const values=[...input];
input[0].value=source();
// ruleid: flow
sink(values[0].value);
