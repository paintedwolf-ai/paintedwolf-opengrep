let values;
if (condition()) values=['fixed'];
else values=['fixed','other'];
values.push(source());
// ok: flow
sink(values[0]);
// ruleid: flow
sink(values[1]);
// ruleid: flow
sink(values[2]);
