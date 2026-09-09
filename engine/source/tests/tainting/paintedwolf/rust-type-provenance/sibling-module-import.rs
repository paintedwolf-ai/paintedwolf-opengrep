mod inner { mod reqwest {} } use reqwest::Client; fn f() {
// ruleid: client-factory
Client::builder(); }
