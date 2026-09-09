
fn f() {
// ruleid: flow
sink(source().parse::<core::primitive::u64>().unwrap());
}
mod core { pub mod primitive { pub type u64 = String; } }
