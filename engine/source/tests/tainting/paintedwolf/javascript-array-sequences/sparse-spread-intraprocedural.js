const input=[];
input[2]='fixed';
const values=[...input];
values.push(source());
// ok: flow
sink(values[1]);
// ruleid: flow
sink(values[3]);
