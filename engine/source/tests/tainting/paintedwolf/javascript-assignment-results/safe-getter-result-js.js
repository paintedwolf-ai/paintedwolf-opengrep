function test() {
const box = {set field(value) {}, get field() {return source();}}; const value = box.field = "fixed";
// ok: flow
observe(value);
}
