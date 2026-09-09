async function run(flag) {
 let db = await openDB();
 db = {};
 execute(db, source());
}
