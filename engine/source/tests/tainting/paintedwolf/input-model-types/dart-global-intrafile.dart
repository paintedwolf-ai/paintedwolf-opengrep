final client = Model();
void run() {
 // ruleid: flow
 sink(client);
}
final literal = 'fixed';
void safe() {
 // ok: flow
 sink(literal);
}
