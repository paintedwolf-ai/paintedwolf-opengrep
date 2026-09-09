const values=['fixed',...externalArray()];
values.push(source());
// ok: flow
sink(values[0]);
// ruleid: flow
sink(values[1]);
