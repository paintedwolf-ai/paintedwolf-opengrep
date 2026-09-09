register(({nested: {client: request, unrelated}}) => {
  const alias = request;
  // ruleid: flow
  sink(alias);
  sink(unrelated);
  request = "fixed";
  sink(request);
});
