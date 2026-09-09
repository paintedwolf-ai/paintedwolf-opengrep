function run() {
 const client = new Model();
 // ruleid: flow
 sink(client);
 // ruleid: flow
 sink(new Model());
 // ruleid: flow
 sink((new Model()));
 // ok: flow
 sink(new Other());
 // ok: flow
 sink([new Model()]);
}
