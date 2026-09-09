const input=[{value:source()}];
const values=[...input];
input[0]={value:'fixed'};
// ruleid: flow
sink(values[0].value);
