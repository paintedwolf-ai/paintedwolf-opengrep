const values=[];
values.push=function(value){ return value; };
// ruleid: flow
sink(values.push(source()));
