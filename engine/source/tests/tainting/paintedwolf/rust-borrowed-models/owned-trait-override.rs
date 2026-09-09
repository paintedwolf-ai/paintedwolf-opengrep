trait CustomParse { fn parse<T>(&self) -> Result<String, ()>; } impl CustomParse for String { fn parse<T>(&self) -> Result<String, ()> { Ok(self.clone()) } } fn f() {
// ruleid: flow
sink(owned().parse::<u64>().unwrap()); }
