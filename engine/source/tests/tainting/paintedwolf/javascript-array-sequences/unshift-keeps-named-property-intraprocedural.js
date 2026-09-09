const item={value:'fixed'};
const values=[];
values.named=item;
values.unshift('fixed');
item.value=source();
// ruleid: flow
sink(values.named.value);
