function append(value){const values=[]; values.push(value); return values;}
const result=append(source());
// ruleid: flow
sink(result[0]);
