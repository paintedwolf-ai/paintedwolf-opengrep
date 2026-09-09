const values=[source()];
values.length=0;
values.push('fixed');
// ok: flow
sink(values[0]);
