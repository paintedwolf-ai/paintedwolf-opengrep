mod child { extern crate std as system; } fn h(){system::process::Command::new("sh");}
