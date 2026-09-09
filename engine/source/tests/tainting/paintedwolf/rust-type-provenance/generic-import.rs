use axum::extract::Query;
// ruleid: query-type,query-whole-type
fn f(q: Query<Params>) {}
