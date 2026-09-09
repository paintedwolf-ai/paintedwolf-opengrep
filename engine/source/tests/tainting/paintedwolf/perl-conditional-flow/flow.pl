my $value = source();
# ruleid: flow
sink($value) if $condition;
# ruleid: flow
sink($value) unless $condition;
if ($condition) {
  # ruleid: flow
  sink($value);
} elsif ($other) {
  # ruleid: flow
  sink($value);
} else { sink('fixed'); }
my $choice = $condition ? source() : 'fixed';
# ruleid: flow
sink($choice);
my $safe = $condition ? 'fixed' : 'also fixed';
sink($safe);
my $overwritten = source();
$overwritten = 'fixed' if $condition;
# ruleid: flow
sink($overwritten);
my $unless_value = source();
$unless_value = 'fixed' unless $condition;
# ruleid: flow
sink($unless_value);
# ruleid: flow
sink($value) unless '0';
# ruleid: flow
sink($value) if 'safe';
sink('fixed') if $condition;
sink('fixed') unless $condition;
sink($value) if 0;
sink($value) unless 1;
sink($value) if '0';
sink($value) if '';
my $zero = '0';
sink($value) if $zero;
# ruleid: flow
sink($value) unless $zero;
my $empty = '';
sink($value) if $empty;
my $numeric_zero = 0;
sink($value) if $numeric_zero;
my $truthy = '0e0';
# ruleid: flow
sink($value) if $truthy;
sink($value) unless $truthy;
sink($value) if 0.0;
sink($value) if undef;
# ruleid: flow
sink($value) if 0.5;
my $undefined = undef;
sink($value) if $undefined;
