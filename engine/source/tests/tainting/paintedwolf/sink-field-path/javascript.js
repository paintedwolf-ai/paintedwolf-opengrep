// ruleid: flow
sink({url: source(), body: "safe"});
sink({url: "https://example.com/", body: source()});
const options = {url: source()};
// ruleid: flow
sink(options);
options.url = "https://example.com/";
sink(options);
options.body = source();
sink(options);
options.url = source();
const alias = options;
// ruleid: flow
sink(alias);
