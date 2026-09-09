use axum::extract::Query;
fn outer() { struct Query<T>(T); fn f(q: Query<Params>) {} }
