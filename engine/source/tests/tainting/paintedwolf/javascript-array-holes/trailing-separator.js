const values = [source(),];
// ruleid: flow
sink(values[0]);
// ok: flow
sink(values[1]);
