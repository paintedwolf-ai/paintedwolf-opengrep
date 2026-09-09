function test() {
const box = {}; const value = box.field = source();
// ruleid: flow
observe(value);
}
