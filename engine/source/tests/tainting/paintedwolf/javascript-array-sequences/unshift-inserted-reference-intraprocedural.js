const item={value:'fixed'};
const values=[{value:'other'}];
values.unshift(item);
item.value=source();
// ruleid: flow
sink(values[0].value);
// ok: flow
sink(values[1].value);
