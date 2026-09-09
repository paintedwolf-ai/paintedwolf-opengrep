import type {NextApiRequest} from "next";
function factory() {
type NextApiRequest = {query:string};
// ok: binding
function handler(req: NextApiRequest) {}
}
