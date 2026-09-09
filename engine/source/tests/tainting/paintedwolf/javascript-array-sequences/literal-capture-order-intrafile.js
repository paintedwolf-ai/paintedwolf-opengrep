let input=source();
const values=[input,(input='fixed')];
// ruleid: flow
sink(values[0]);
// ok: flow
sink(values[1]);
