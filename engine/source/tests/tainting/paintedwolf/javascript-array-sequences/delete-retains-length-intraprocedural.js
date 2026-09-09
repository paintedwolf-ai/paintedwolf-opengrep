const values=['fixed','other'];
delete values[1];
values.push(source());
// ok: flow
sink(values[1]);
// ruleid: flow
sink(values[2]);
