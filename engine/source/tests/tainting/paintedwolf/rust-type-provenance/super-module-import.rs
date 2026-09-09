mod reqwest { pub struct Client; } mod inner { use super::reqwest::Client; fn f() { Client::builder(); } }
