my $appended = source();
$appended .= '/suffix';
# ruleid: flow
sink($appended);
my $prefix = 'prefix/';
$prefix .= source();
# ruleid: flow
sink($prefix);
my $fixed = 'prefix/';
$fixed .= 'suffix';
sink($fixed);
my %fields = (unsafe => source(), safe => 'fixed');
$fields{unsafe} .= '/suffix';
# ruleid: flow
sink($fields{unsafe});
sink($fields{safe});
my $overwritten = source();
$overwritten = 'fixed';
sink($overwritten);
my $and_skipped = '0';
$and_skipped &&= source();
sink($and_skipped);
my $and_taken = 'yes';
$and_taken &&= source();
# ruleid: flow
sink($and_taken);
my $or_skipped = 'fixed';
$or_skipped ||= source();
sink($or_skipped);
my $or_taken = '';
$or_taken ||= source();
# ruleid: flow
sink($or_taken);
my $defined_zero = '0';
$defined_zero //= source();
sink($defined_zero);
my $defined_empty = '';
$defined_empty //= source();
sink($defined_empty);
my $undefined = undef;
$undefined //= source();
# ruleid: flow
sink($undefined);
my $retained = source();
$retained //= 'fixed';
# ruleid: flow
sink($retained);
my $and_effect = 'fixed';
my $false = 0;
$false &&= ($and_effect = source());
sink($and_effect);
my $or_effect = 'fixed';
my $true = 1;
$true ||= ($or_effect = source());
sink($or_effect);
my $defined_effect = 'fixed';
my $defined = '';
$defined //= ($defined_effect = source());
sink($defined_effect);
my $taken_effect = 'fixed';
my $missing = undef;
$missing //= ($taken_effect = source());
# ruleid: flow
sink($taken_effect);
