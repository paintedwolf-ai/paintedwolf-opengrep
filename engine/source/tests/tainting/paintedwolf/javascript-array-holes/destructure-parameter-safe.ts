function read([,value]) {
// ok: flow
sink(value);
}
read([source(),"fixed"]);
