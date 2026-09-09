function capturedReturn() {
  let value = source();
  try {
    return value;
  } finally {
    value = "safe";
  }
}
// ruleid: flow
sink(capturedReturn());

function overriddenReturn() {
  try {
    return source();
  } finally {
    return "safe";
  }
}
sink(overriddenReturn());

function breakCleanup() {
  let value = source();
  while (true) {
    try {
      break;
    } finally {
      value = "safe";
    }
  }
  sink(value);
}

function nestedOrder() {
  let value = "safe";
  try {
    try {
      return value;
    } finally {
      value = source();
    }
  } finally {
    // ruleid: flow
    sink(value);
  }
}

function throwOverridesReturn() {
  try {
    return "safe";
  } finally {
    throw source();
  }
}
function catchFinalizerThrow() {
  try {
    throwOverridesReturn();
  } catch (error) {
    // ruleid: flow
    sink(error);
  }
}
