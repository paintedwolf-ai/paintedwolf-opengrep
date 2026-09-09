const client = make_model();
function run() {
 // ruleid: flow
 sink(client);
}
const literal = 'fixed';
function safe() {
 // ok: flow
 sink(literal);
}
