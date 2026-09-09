const values=['fixed'];
values.length=3;
values.push(source());
// ok: flow
sink(values[1]);
// ruleid: flow
sink(values[3]);
