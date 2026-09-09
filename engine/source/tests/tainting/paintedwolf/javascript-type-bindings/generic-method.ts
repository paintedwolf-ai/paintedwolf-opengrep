import type {NextApiRequest} from "next";
class Factory {create<NextApiRequest>() {
// ok: binding
function handler(req: NextApiRequest) {}
}}
