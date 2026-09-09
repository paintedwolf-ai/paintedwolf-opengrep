function handler({request}) {
 // ruleid: flow
 sink(request);
 request = null;
 // ok: flow
 sink(request);
}
const callback = ({request}) => {
 // ruleid: flow
 sink(request);
};
