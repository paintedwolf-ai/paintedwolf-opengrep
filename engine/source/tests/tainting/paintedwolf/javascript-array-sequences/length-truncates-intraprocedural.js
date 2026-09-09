const values=['fixed',source()];
values.length=1;
values.push('safe');
// ok: flow
sink(values[1]);
