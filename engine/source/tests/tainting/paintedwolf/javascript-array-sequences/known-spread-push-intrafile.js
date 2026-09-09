const prefix=['fixed','other'];
const values=[...prefix];
values.push(source());
// ok: flow
sink(values[1]);
// ruleid: flow
sink(values[2]);
