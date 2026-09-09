let values;
if (condition()) values=['fixed'];
else values=externalArray();
values.push(source());
// ruleid: flow
sink(values[0]);
