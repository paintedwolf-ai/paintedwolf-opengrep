use axum::extract::Query as Incoming;
// ruleid: query-type,query-whole-type
fn f(q: Incoming<Params>) {}
