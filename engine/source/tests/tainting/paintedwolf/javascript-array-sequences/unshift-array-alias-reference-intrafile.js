const item={value:'fixed'};
const values=[item];
const alias=values;
alias.unshift({value:'other'});
item.value=source();
// ok: flow
sink(values[0].value);
// ruleid: flow
sink(values[1].value);
