function test() {
let input = "fixed"; const box = {set field(value) {input = source();}}; const value = box.field = input;
// ok: flow
observe(value);
}
