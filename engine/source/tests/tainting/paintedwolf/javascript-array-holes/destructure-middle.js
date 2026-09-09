const [first,,last] = ["fixed", "fixed", source()];
// ruleid: flow
sink(last);
// ok: flow
sink(first);
