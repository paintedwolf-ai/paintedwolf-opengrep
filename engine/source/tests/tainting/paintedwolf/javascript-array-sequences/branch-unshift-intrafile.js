let values;
if (condition()) values=[source()];
else values=['fixed'];
values.unshift('safe');
// ok: flow
sink(values[0]);
// ruleid: flow
sink(values[1]);
