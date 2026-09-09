const input=[source()];
const values=[...input,(input[0]='fixed')];
// ruleid: flow
sink(values[0]);
// ok: flow
sink(values[1]);
