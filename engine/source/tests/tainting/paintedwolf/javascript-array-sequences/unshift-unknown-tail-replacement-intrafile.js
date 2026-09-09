const item={value:'fixed'};
const values=[item];
values.unshift({value:'fixed'},...external());
values[2]={value:source()};
// ok: flow
sink(item.value);
// ruleid: flow
sink(values[2].value);
