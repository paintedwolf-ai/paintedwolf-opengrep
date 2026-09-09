const values=['fixed'];
values.push('other',source(),'last');
// ok: flow
sink(values[1]);
// ruleid: flow
sink(values[2]);
// ok: flow
sink(values[3]);
