const values=[];
const length=values.push(source());
// ok: flow
sink(length);
// ok: flow
sink(values.length);
