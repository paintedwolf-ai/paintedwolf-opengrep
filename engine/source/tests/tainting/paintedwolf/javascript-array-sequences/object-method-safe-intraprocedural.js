const values={push(value){return 'fixed';}};
// ok: flow
sink(values.push(source()));
