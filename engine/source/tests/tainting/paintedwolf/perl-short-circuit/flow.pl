my $input = source();
0 && sink($input);
'0' && sink($input);
'' && sink($input);
undef && sink($input);
'yes' || sink($input);
1 || sink($input);
'0' // sink($input);
'' // sink($input);
# ruleid: flow
1 && sink($input);
# ruleid: flow
'yes' && sink($input);
# ruleid: flow
0 || sink($input);
# ruleid: flow
'' || sink($input);
# ruleid: flow
undef // sink($input);
0 and sink($input);
'yes' or sink($input);
# ruleid: flow
1 and sink($input);
# ruleid: flow
0 or sink($input);
my $effect = 'fixed';
0 && ($effect = source());
sink($effect);
my $alternate = 'fixed';
'yes' || ($alternate = source());
sink($alternate);
my $default = 'fixed';
'' // ($default = source());
sink($default);
my $chosen = undef // source();
# ruleid: flow
sink($chosen);
my $retained = source() // 'fixed';
# ruleid: flow
sink($retained);
my $safe = 'fixed' || source();
sink($safe);
my $empty = '' && source();
sink($empty);
