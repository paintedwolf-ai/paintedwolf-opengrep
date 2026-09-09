import type {NextApiRequest} from "next";
const factory = function<NextApiRequest>() {
// ok: binding
function handler(req: NextApiRequest) {}
};
