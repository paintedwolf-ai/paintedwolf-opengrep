const callbacks = [() => "fixed",,value => {
// ruleid: flow
sink(value);
}];
callbacks[2](source());
