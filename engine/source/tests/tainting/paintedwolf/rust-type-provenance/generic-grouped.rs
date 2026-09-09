use axum::extract::{Path, Query};
// ruleid: query-type,query-whole-type
fn f(q: Query<Params>) {}
