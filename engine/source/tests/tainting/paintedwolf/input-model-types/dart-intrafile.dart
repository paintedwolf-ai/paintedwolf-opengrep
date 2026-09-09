void handler(dynamic request) {
 // ruleid: flow
 sink(request);
 final alias = request;
 // ruleid: flow
 sink(alias);
 // ok: flow
 sink(request.context);
 request = null;
 // ok: flow
 sink(request);
}
