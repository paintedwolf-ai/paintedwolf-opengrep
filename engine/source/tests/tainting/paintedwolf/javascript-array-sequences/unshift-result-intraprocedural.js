const values=['fixed'];
const length=values.unshift(source());
// ok: flow
sink(length);
// ok: flow
sink(values.length);
