func handler() async throws {
 // ruleid: flow
 _ = try await db.raw(input).all()
}
