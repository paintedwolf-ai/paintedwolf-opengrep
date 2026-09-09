import type {NextApiRequest} from "next";
class Factory<NextApiRequest> {create() {
// ok: binding
function handler(req: NextApiRequest) {}
}}
