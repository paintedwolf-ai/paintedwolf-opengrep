register(({client: request, unrelated}) => {
  // ruleid: flow
  sink(request);
  sink(unrelated);
});
