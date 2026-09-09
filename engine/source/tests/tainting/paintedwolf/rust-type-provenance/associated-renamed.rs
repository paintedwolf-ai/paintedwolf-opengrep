use std::process::Command as Spawn;
fn f() {
// ruleid: command-factory
Spawn::new("sh");
}
