import type {NextApiRequest} from "next";
const factory = <NextApiRequest>() => {
// ok: binding
function handler(req: NextApiRequest) {}
};
