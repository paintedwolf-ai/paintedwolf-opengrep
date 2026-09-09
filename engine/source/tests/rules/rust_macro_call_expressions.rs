fn handler() {
    let value = source();
    let command = format!("{}", value.trim());
    // ruleid: format-flow
    sink(command);
    let nested = format!("{}", wrap(value.trim()),);
    // ruleid: format-flow
    sink(nested);
    let safe = format!("{}", "fixed".trim());
    sink(safe);
    let chained = format!("{}", value.trim().to_string());
    // ruleid: format-flow
    sink(chained);
    let called = format!("{}", source(),);
    // ruleid: format-flow
    sink(called);
    let safe_trailing = format!("{}", "fixed".trim(),);
    sink(safe_trailing);
    let sibling = format!("{}", harmless(),);
    sink(sibling);
}
