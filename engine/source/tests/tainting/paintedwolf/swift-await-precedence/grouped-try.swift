func handler() async throws {
 _ = (try db.raw(input)).all()
}
