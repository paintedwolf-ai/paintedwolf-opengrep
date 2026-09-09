const values = [,source()];
// ruleid: flow
sink(values[1]);
// ok: flow
sink(values[0]);
