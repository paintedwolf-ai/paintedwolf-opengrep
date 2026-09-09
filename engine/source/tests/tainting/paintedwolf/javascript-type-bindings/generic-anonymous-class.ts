import type {NextApiRequest} from "next";
const Factory=class<NextApiRequest> {create() {
// ok: binding
function handler(req: NextApiRequest) {}
}};
