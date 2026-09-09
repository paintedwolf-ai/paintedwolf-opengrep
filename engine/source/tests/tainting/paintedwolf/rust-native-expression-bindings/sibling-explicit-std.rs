#![no_std]
mod child { extern crate std; } fn h(){std::process::Command::new("sh");}
