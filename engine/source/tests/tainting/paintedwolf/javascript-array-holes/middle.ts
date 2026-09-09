const values = ["fixed",,source()];
// ruleid: flow
sink(values[2]);
// ok: flow
sink(values[1]);
