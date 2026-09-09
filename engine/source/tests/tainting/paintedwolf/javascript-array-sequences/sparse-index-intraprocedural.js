const values=[];
values[3]='fixed';
values.push(source());
// ok: flow
sink(values[0]);
// ok: flow
sink(values[3]);
// ruleid: flow
sink(values[4]);
