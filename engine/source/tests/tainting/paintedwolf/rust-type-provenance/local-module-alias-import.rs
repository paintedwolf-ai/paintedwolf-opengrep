mod reqwest { pub struct Client; } use reqwest as http; use http::Client; fn f() { Client::builder(); }
