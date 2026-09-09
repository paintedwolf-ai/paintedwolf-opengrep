mod std { pub mod process { pub struct Command; } }
fn h(){
// ruleid: native-api
::std::process::Command::new("sh");
}
