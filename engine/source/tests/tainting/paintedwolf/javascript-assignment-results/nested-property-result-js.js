function test() {
const first = {set field(value) {}}; const second = {set field(value) {}}; const value = first.field = second.field = source();
// ruleid: flow
observe(value);
}
