import Vapor
import Foundation
func outer() {
 struct Request {}
 // ok: origin
 func handler(req: Request) {}
}
