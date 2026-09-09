function test() {
let assigned = source(); const value = assigned = "fixed";
// ok: flow
observe(value);
}
