struct Other; trait Fake { fn new(value:&str)->Other; } impl Fake for std::process::Command { fn new(_: &str)->Other{Other} } type Alias = std::process::Command;
fn h(){let _:Other=<Alias as Fake>::new("sh");}
