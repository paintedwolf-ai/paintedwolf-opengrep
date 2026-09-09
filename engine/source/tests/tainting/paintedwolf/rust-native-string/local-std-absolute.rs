mod std { pub mod string { pub struct String; } }
// ruleid: string-type
fn f(value: ::std::string::String) { }
