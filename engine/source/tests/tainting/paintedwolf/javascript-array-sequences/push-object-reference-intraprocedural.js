const item={value:'fixed'};
const values=[];
values.push(item);
item.value=source();
// ruleid: flow
sink(values[0].value);
