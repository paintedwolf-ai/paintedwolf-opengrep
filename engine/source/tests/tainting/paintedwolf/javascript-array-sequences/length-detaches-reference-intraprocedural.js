const item={value:'fixed'};
const values=[item];
values.length=0;
values.push({value:'other'});
item.value=source();
// ok: flow
sink(values[0].value);
