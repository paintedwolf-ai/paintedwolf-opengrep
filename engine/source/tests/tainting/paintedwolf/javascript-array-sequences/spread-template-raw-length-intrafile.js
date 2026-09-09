function tag(strings,value){const values=[...strings.raw]; values.push(value); return values[2];}
// ruleid: flow
sink(tag`fixed${source()}tail`);
