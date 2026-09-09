// ruleid: flow
sink({0: source()});
// ruleid: flow
sink({"0": source()});
sink({"00": source(), "0": "safe"});
// ruleid: flow
sink([source()]);
sink(["safe", source()]);
sink({"0.": source(), "0": "safe"});
// ruleid: flow
sink({0x0: source()});
// ruleid: flow
sink({0e0: source()});
