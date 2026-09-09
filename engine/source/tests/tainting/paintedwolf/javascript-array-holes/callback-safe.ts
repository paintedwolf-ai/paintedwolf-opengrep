const callbacks = [,value => {
// ok: flow
sink(value);
}];
callbacks[1]("fixed");
