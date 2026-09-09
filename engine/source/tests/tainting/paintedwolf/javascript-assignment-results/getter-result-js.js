function test() {
const box = {set field(value) {}, get field() {return "fixed";}}; const value = box.field = source();
// ruleid: flow
observe(value);
}
