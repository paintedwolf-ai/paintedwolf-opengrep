const item={value:'fixed'};
const values=[];
values.push(item);
values[0]={value:'other'};
item.value=source();
// ok: flow
sink(values[0].value);
