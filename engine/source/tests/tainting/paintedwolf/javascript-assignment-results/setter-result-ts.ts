function test() {
const box = {set field(value) {}}; const value = box.field = source();
// ruleid: flow
observe(value);
}
