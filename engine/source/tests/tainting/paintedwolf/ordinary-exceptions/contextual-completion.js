function mutateThenThrow(original, box) {
  box.value = "TAINTED";
  throw original;
}

function distinctCompletions() {
  const box = {value: "safe"};
  try {
    mutateThenThrow(box.value, box);
    // ok: flow
    sink("TAINTED");
  } catch (error) {
    // ok: flow
    sink(error);
    // ruleid: flow
    sink(box.value);
  }
}

function thrownLiteral() {
  const box = {value: "safe"};
  try {
    mutateThenThrow("TAINTED", box);
  } catch (error) {
    // ruleid: flow
    sink(error);
  }
}
