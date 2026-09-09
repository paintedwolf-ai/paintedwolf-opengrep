register(({unrelated, ...context}) => {
  // ruleid: flow
  sink(context.client);
  sink(unrelated);
});
