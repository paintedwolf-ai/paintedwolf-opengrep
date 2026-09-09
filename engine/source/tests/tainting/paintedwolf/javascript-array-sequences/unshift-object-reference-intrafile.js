const item={value:'fixed'};
const values=[item];
values.unshift({value:'other'});
item.value=source();
// ok: flow
sink(values[0].value);
// ruleid: flow
sink(values[1].value);
