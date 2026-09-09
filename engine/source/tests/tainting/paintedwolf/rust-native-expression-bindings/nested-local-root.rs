mod child {mod std {} fn h(){std::process::Command::new("sh");}}
fn h(){
// ruleid: native-api
std::process::Command::new("sh");}
