mod std { pub mod process { pub struct Command; } }
fn h(){
std::process::Command::new("sh");
}
