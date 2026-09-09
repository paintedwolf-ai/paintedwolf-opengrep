const values=[];
values.push(source());
values[0]='fixed';
// ok: flow
sink(values[0]);
