struct Other; trait Fake { fn new(value:&str)->Other; } impl Fake for std::process::Command { fn new(_: &str)->Other{Other} } type Alias = std::process::Command;
fn h(){
// ruleid: native-api
let _: std::process::Command = Alias::new("sh");}
