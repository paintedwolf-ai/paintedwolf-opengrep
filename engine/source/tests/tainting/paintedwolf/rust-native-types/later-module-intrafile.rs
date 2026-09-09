use core::primitive::u64 as Count; fn f() {
// ruleid: flow
sink(source().parse::<Count>().unwrap());
}
mod core { pub mod primitive { pub type u64 = String; } }
