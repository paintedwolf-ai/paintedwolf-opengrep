func handler() async throws {
 // ruleid: flow
 _ = try db.raw(input).all()
}
