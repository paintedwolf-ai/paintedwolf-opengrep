const values=[];
values[0]=values;
values.unshift({value:'fixed'});
values.value=source();
// ok: flow
sink(values[0].value);
// ruleid: flow
sink(values[1].value);
