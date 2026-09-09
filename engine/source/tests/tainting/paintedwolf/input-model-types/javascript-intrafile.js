function handler(request) {
 // ruleid: flow
 sink(request);
 const alias = request;
 // ruleid: flow
 sink(alias);
 // ok: flow
 sink(request.context);
 request = null;
 // ok: flow
 sink(request);
}
