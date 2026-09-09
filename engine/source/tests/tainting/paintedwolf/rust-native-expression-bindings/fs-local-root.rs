mod std { pub mod fs {} }
fn h(){
std::fs::canonicalize("/srv");
}
