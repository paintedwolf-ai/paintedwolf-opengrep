mod inner { mod reqwest { pub struct Client; } use reqwest::Client; fn f() { Client::builder(); } }
