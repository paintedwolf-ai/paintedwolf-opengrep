const values=[source()];
values.unshift('fixed','other');
// ok: flow
sink(values[0]);
// ok: flow
sink(values[1]);
// ruleid: flow
sink(values[2]);
