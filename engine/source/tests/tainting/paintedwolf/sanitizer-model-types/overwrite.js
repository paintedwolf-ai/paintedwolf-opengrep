function f() { const box = {value: source()}; box.value = opaque(source());
// ruleid: flow
sink(box.value.length); }
