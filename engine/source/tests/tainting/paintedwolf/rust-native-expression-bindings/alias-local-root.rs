mod std {pub mod process {pub struct Command;}} type Cmd=std::process::Command; fn h(){Cmd::new("sh");}
