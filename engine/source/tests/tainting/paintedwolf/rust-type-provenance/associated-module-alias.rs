use reqwest as http;
fn f() {
// ruleid: client-factory
http::Client::builder();
}
