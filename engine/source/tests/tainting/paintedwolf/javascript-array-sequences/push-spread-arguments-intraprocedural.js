const values=['fixed'];
values.push(...['other',source()]);
// ok: flow
sink(values[1]);
// ruleid: flow
sink(values[2]);
