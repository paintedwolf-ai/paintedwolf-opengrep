register((context) => {
  // ruleid: flow
  sink(context.client);
  sink(context.unrelated);
});
