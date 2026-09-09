const item={value:'fixed'};
const removed={value:'other'};
const values=[item,removed];
values.length=1;
item.value=source();
// ruleid: flow
sink(values[0].value);
