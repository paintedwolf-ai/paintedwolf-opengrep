function test() {
let input = source(); const box = {set field(value) {input = "fixed";}}; const value = box.field = input;
// ruleid: flow
observe(value);
}
