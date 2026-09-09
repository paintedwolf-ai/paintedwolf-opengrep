import type {NextApiRequest} from "next";
function factory<NextApiRequest>() {
// ok: binding
function handler(req: NextApiRequest) {}
}
