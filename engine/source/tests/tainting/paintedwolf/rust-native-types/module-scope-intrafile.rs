type u64 = String; mod inner { fn f() { sink(source().parse::<u64>().unwrap()); } }
