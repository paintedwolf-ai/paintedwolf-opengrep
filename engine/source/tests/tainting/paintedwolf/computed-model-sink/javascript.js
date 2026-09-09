// ruleid: flow
sink(makeModel());
const model = makeModel();
// ruleid: flow
sink(model);
// ruleid: flow
sink((makeModel()));
// ok: flow
sink("safe");
// ok: flow
sink(otherFactory());
// ok: flow
sink([makeModel()]);
// ok: flow
sink(opaque(makeModel()));
