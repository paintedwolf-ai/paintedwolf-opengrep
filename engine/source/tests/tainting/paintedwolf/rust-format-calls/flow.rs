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
    let sibling = format!("{}", harmless(),);
    sink(sibling);
}
