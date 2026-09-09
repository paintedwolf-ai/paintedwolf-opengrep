function caught() {
  try { throw source(); }
  catch (problem) {
    // ruleid: flow
    sink(problem);
  }
}
function safeCaught() {
  const unrelated = source();
  try { throw "safe"; }
  catch (problem) { sink(problem); }
}
function optionalCatch() {
  try { throw source(); }
  catch { sink("safe"); }
}
function destructuredCatch() {
  try { throw {bad: source(), good: "safe"}; }
  catch ({bad, good}) {
    // ruleid: flow
    sink(bad);
    sink(good);
  }
}
function nestedCatch() {
  try {
    try { throw source(); }
    catch (inner) { throw inner; }
  } catch (outer) {
    // ruleid: flow
    sink(outer);
  }
}

function lexicalCatch() {
  const problem = source();
  try { throw "safe"; }
  catch (problem) { sink(problem); }
  // ruleid: flow
  sink(problem);
}
